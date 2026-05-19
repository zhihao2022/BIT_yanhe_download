import multiprocessing
import threading
import time
import uuid
import webbrowser
from queue import Empty, Queue

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

import m3u8dl
import utils

app = Flask(__name__, static_folder="webui")

"""
    {
        "url":
        "output":
        "name":
        "cur":
        "tot":
        "uuid":
        "canceled":
        "merge_status": 
        "download_type":
        "download_mode": video | audio
        "download_audio": bool
        "audio_sources":
    }
"""
all_task_status = []


"""
    {
        "uuid"
    }
"""
task_queue = Queue()


def find_all_task_by_uuid(uuid):
    for id, task in enumerate(all_task_status):
        if task["uuid"] == uuid:
            return task, id
    return None


g_father_queue = None
current_task_uuid = ""


def executor_progress_callback(cur, tot, merge_status):
    global g_father_queue, current_task_uuid
    g_father_queue.put(
        {
            "uuid": current_task_uuid,
            "cur": cur,
            "tot": tot,
            "merge_status": merge_status,
        }
    )
    # print({
    #     "uuid": current_task_uuid,
    #     "cur": cur,
    #     "tot": tot,
    #     "merge_status": merge_status
    # })
    return False


def execute_one_download_task_worker(task_dict, father_queue):
    global current_task_uuid, g_father_queue
    print(f"downloading task {task_dict}")
    current_task_uuid = task_dict["uuid"]
    output = task_dict["output"]
    name = task_dict["name"]
    audio_sources = task_dict.get("audio_sources", [])
    g_father_queue = father_queue

    if task_dict.get("download_mode") == "audio":
        download_audio_sources(audio_sources, output, name, father_queue)
        return

    url = task_dict["url"]
    m3u8dl.M3u8Download(url, output, name, progress_callback=executor_progress_callback)
    if task_dict["download_audio"] and audio_sources:
        download_audio_sources(audio_sources, output, name, father_queue)
    return


def download_audio_sources(audio_sources, output, name, father_queue):
    total = len(audio_sources)
    father_queue.put(
        {
            "uuid": current_task_uuid,
            "cur": 0,
            "tot": total,
            "merge_status": 3,
        }
    )
    for index, source in enumerate(audio_sources):
        print(f"Downloading audio source {source.get('index', index + 1)}...")
        suffix = "" if total == 1 else f"-audio-{source.get('index', index + 1)}"
        utils.download_audio(source["url"], output, name, suffix=suffix)
        father_queue.put(
            {
                "uuid": current_task_uuid,
                "cur": index + 1,
                "tot": total,
                "merge_status": 3,
            }
        )
    father_queue.put(
        {
            "uuid": current_task_uuid,
            "cur": total,
            "tot": total,
            "merge_status": 2,
        }
    )


def execute_tasks():
    global all_task_status
    queue = multiprocessing.Queue()
    while True:
        try:
            task = task_queue.get(timeout=1)
            task_uuid = task["uuid"]
            task_obj, task_id = find_all_task_by_uuid(task_uuid)
            if task_obj["canceled"] is True:
                all_task_status.pop(task_id)
                continue
            process = multiprocessing.Process(
                target=execute_one_download_task_worker, args=(task_obj, queue)
            )
            process.start()
            while True:
                if all_task_status[task_id]["canceled"]:
                    print("task canceled, terminate subprocess...")
                    process.terminate()
                    all_task_status.pop(task_id)
                    break
                try:
                    msg = queue.get_nowait()
                    update_obj, update_id = find_all_task_by_uuid(msg["uuid"])
                    all_task_status[update_id]["cur"] = msg["cur"]
                    all_task_status[update_id]["tot"] = msg["tot"]
                    all_task_status[update_id]["merge_status"] = msg["merge_status"]
                except Empty:
                    if process.is_alive() is False:
                        break
                    time.sleep(0.1)
                    continue
                except TypeError:
                    continue
        except Empty:
            continue
        except TypeError:
            continue


@app.route("/")
def index():
    auth = utils.read_auth()
    return render_template(
        "index.html",
        auth=auth,
        auth_prompt="" if auth else "。".join(utils.auth_prompt()),
    )


@app.route("/get_course")
def get_course():
    course_id = request.args.get("course_id")
    auth = request.args.get("auth")
    if auth:
        utils.write_auth(auth)
    if not utils.test_auth(courseID=course_id):
        utils.remove_auth()
        return jsonify({"code": 403, "msg": "。".join(utils.auth_prompt(False))})
    try:
        videoList, courseName, professor = utils.get_course_info(courseID=course_id)
    except Exception:
        return jsonify({"videoList": [], "courseName": "", "professor": ""})
    return jsonify(
        {"videoList": videoList, "courseName": courseName, "professor": professor}
    )


@app.route("/new_task", methods=["POST"])
def new_task():
    global task_queue, all_task_status
    data = request.json
    course_id = data["course_id"]
    course_number = data["course_number"]
    download_version = data["download_version"]
    audio_source_mode = data.get("audio_source_mode")
    if audio_source_mode is None:
        audio_source_mode = "first" if data.get("download_audio") == "1" else "none"
    if download_version == "3" and audio_source_mode == "none":
        audio_source_mode = "all"
    videoList, courseName, professor = utils.get_course_info(courseID=course_id)
    course_number_arr = course_number.split(",")
    ret_id = []
    for courseNum in course_number_arr:
        courseNumT = int(courseNum)
        c = videoList[courseNumT]
        name = courseName + "-" + professor + "-" + c["title"]
        print(name)

        cur_uuid = str(uuid.uuid4())
        ret_id.append(cur_uuid)
        task_status = {
            "url": "",
            "output": "",
            "name": name,
            "cur": 0,
            "tot": 0,
            "uuid": cur_uuid,
            "canceled": False,
            "merge_status": 0,
            "download_type": download_version,
            "download_mode": "audio" if download_version == "3" else "video",
            "download_audio": audio_source_mode != "none",
            "audio_source_mode": audio_source_mode,
            "audio_sources": [],
            "audio_url": "",
        }

        audio_sources = utils.get_audio_sources(c.get("video_ids", []))
        if audio_source_mode == "first":
            audio_sources = audio_sources[:1]
        elif audio_source_mode == "none" and download_version != "3":
            audio_sources = []
        task_status["audio_sources"] = audio_sources
        task_status["audio_url"] = audio_sources[0]["url"] if audio_sources else ""
        task_status["download_audio"] = bool(audio_sources)
        if download_version == "2":
            print("Downloading screen...")
            task_status["url"] = c["videos"][0]["vga"]
            task_status["output"] = "output/" + courseName + "-screen"
        elif download_version == "3":
            print("Downloading audio...")
            task_status["output"] = "output/" + courseName + "-audio"
        else:
            print("Downloading video...")
            task_status["url"] = c["videos"][0]["main"]
            task_status["output"] = "output/" + courseName + "-video"
        all_task_status.append(task_status)
        task_queue.put({"uuid": cur_uuid})

    return jsonify({"status": "success", "task_id": ret_id})


@app.route("/get_status")
def get_status():
    global all_task_status
    return jsonify(all_task_status)


@app.route("/kill_task")
def kill_task():
    global all_task_status
    uuid = request.args.get("uuid")
    task, id = find_all_task_by_uuid(uuid)
    if task["merge_status"] == 2:
        # if already finished
        all_task_status.pop(id)
        return jsonify({"status": "ok"})
    all_task_status[id]["canceled"] = True
    return jsonify({"status": "ok"})


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    t = threading.Thread(target=execute_tasks)
    t.start()
    webbrowser.open("http://127.0.0.1:5001/")
    app.run(debug=False, host="0.0.0.0", use_reloader=False, port=5001)
