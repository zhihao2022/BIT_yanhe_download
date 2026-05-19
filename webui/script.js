document.getElementById("newTaskButton").onclick = function () {
  document.getElementById("taskPopup").style.display = "block";
};

document.getElementsByClassName("close")[0].onclick = function () {
  document.getElementById("taskPopup").style.display = "none";
};

document.getElementById("downloadType").onchange = function () {
  const audioSourceMode = document.getElementById("audioSourceMode");
  if (this.value === "3" && audioSourceMode.value === "none") {
    audioSourceMode.value = "all";
  }
};

function fetchCourseNumber() {
  const courseId = encodeURIComponent(document.getElementById("courseId").value);
  const auth = encodeURIComponent(document.getElementById("auth").value);
  fetch(`/get_course?course_id=${courseId}&auth=${auth}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.code && data.code == 403) {
        document.getElementById("auth_prompt").innerHTML = data.msg;
        alert(data.msg);
      }
      document.getElementById("courseName11").innerHTML = `课程名: <b>${data.courseName == "" ? "未知" : data.courseName}</b>`;
      document.getElementById("professor11").innerHTML = `老师: <b>${data.professor == "" ? "未知" : data.professor}</b>`;

      let courseListHTML = "";
      for (let i = 0; i < data.videoList.length; i++) {
        courseListHTML += `<li data-value="${i}">${data.videoList[i].title}</li>`;
      }
      document.getElementById("courseList").innerHTML = courseListHTML;
      bindCourseListEvents();
    })
    .catch((error) => console.error("Error:", error));
}

document.getElementById("taskForm").onsubmit = function (event) {
  event.preventDefault();
  const courseId = document.getElementById("courseId").value.trim();
  if (courseId == "") {
    alert("课程 ID 不能为空");
    return;
  }

  const downloadType = document.getElementById("downloadType").value;
  const audioSourceMode = document.getElementById("audioSourceMode").value;
  if (downloadType === "3" && audioSourceMode === "none") {
    alert("仅音频任务需要至少选择一个音频来源");
    return;
  }

  let selectedIndex = [];
  let courseList = document.getElementById("courseList");
  for (let i = 0; i < courseList.childNodes.length; i++) {
    let child = courseList.childNodes[i];
    if (child.className == "selected") {
      selectedIndex.push(child.getAttribute("data-value"));
    }
  }
  if (selectedIndex.length === 0) {
    alert("请至少选择一个课程视频");
    return;
  }

  fetch("/new_task", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      course_id: courseId,
      course_number: selectedIndex.join(","),
      download_version: downloadType,
      audio_source_mode: audioSourceMode,
      download_audio: audioSourceMode === "none" ? "2" : "1",
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      document.getElementById("taskPopup").style.display = "none";
    })
    .catch((error) => console.error("Error:", error));
};

function getDownloadStatusText(taskObj) {
  const mergeStatus = taskObj["merge_status"];
  const cur = taskObj["cur"];
  const tot = taskObj["tot"];
  const cancel = taskObj["canceled"];
  if (cancel) {
    return "已取消";
  }
  if (mergeStatus == 0) {
    if (cur == 0 || tot == 0) {
      return "等待中...";
    }
    return `下载中...(${((cur / tot) * 100).toFixed(2)} %)`;
  }
  if (mergeStatus == 1) {
    return "合并视频中...";
  }
  if (mergeStatus == 2) {
    return "已完成";
  }
  if (mergeStatus == 3) {
    if (tot == 0) {
      return "未找到可用音频来源";
    }
    return `下载音频中...(${cur}/${tot})`;
  }
  return "未知状态";
}

function cancelTask(btn) {
  let uuid = btn.getAttribute("data-task-uuid");
  fetch(`/kill_task?uuid=${uuid}`)
    .then((response) => response.json())
    .then(() => {
      let removeNode = document.getElementById(`${uuid}-task`);
      if (removeNode != null) {
        removeNode.parentNode.removeChild(removeNode);
      }
    })
    .catch((error) => console.error("Error:", error));
}

setInterval(() => {
  const addElement = (taskObj) => {
    if (taskObj["canceled"]) {
      return;
    }
    const downloadVersion = getDownloadVersionText(taskObj);
    const html = `
      <div class="task" id="${taskObj["uuid"]}-task">
        <div class="task-info">
          <span>${taskObj["name"]}(${downloadVersion})</span>
          <div class="status-container">
            <span class="status" id="${taskObj["uuid"]}-status">${getDownloadStatusText(taskObj)}</span>
            <button class="cancel-btn" data-task-uuid="${taskObj["uuid"]}" onclick="cancelTask(this);">x</button>
          </div>
        </div>
        <div class="progress-bar">
          <div class="progress" id="${taskObj["uuid"]}-progress"></div>
        </div>
      </div>
    `;
    let taskList = document.getElementById("taskList");
    taskList.innerHTML = html + taskList.innerHTML;
  };

  const updateElement = (taskObj) => {
    const statusEle = document.getElementById(`${taskObj["uuid"]}-status`);
    const progressEle = document.getElementById(`${taskObj["uuid"]}-progress`);
    statusEle.innerText = getDownloadStatusText(taskObj);
    const progress = taskObj["tot"] > 0 ? (100 * taskObj["cur"]) / taskObj["tot"] : 0;
    progressEle.style.width = `${progress.toFixed(2)}%`;
  };

  const removeCanceledElement = (uuidArr) => {
    let allTaskElem = document.getElementsByClassName("task");
    for (let i = 0; i < allTaskElem.length; i++) {
      const uuid = allTaskElem[i].getAttribute("id").replace("-task", "");
      if (!uuidArr.includes(uuid)) {
        allTaskElem[i].parentNode.removeChild(allTaskElem[i]);
      }
    }
  };

  fetch("/get_status")
    .then((response) => response.json())
    .then((data) => {
      let uuidArr = [];
      for (let i = 0; i < data.length; i++) {
        const uuid = data[i]["uuid"];
        if (!data[i]["canceled"]) {
          uuidArr.push(uuid);
        }
        let existEle = document.getElementById(`${uuid}-task`);
        if (existEle == null) {
          addElement(data[i]);
        } else {
          updateElement(data[i]);
        }
      }
      removeCanceledElement(uuidArr);
    })
    .catch((error) => console.error("Error:", error));
}, 1000);

function getDownloadVersionText(taskObj) {
  if (taskObj["download_type"] == "3" || taskObj["download_mode"] == "audio") {
    return "仅音频";
  }
  if (taskObj["download_type"] == "2") {
    return taskObj["download_audio"] ? "电脑屏幕+音频" : "电脑屏幕";
  }
  return taskObj["download_audio"] ? "摄像头+音频" : "摄像头";
}

function bindCourseListEvents() {
  document.querySelectorAll("#courseList li").forEach((item) => {
    item.addEventListener("click", () => {
      item.classList.toggle("selected");
    });
  });
}

bindCourseListEvents();

function selectAll(select) {
  let list = document.getElementById("courseList");
  for (let i = 0; i < list.childNodes.length; i++) {
    list.childNodes[i].className = select ? "selected" : "";
  }
}
