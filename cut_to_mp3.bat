@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

set "INPUT=最优化理论与方法-王钢-第13周 星期二 第2大节.mp4"
set "CUT_MP4=最优化理论与方法-王钢-第13周 星期二 第2大节_前60分钟.mp4"
set "OUTPUT_MP3=最优化理论与方法-王钢-第13周 星期二 第2大节_前60分钟.mp3"

if not exist "%INPUT%" (
    echo 找不到输入文件：
    echo %INPUT%
    pause
    exit /b 1
)

echo 正在截取前60分钟 MP4...
ffmpeg -y -i "%INPUT%" -t 01:00:00 -c copy "%CUT_MP4%"

if errorlevel 1 (
    echo 截取 MP4 失败。
    pause
    exit /b 1
)

echo 正在转换为 MP3...
ffmpeg -y -i "%CUT_MP4%" -vn -acodec libmp3lame -q:a 2 "%OUTPUT_MP3%"

if errorlevel 1 (
    echo 转换 MP3 失败。
    pause
    exit /b 1
)

echo 完成！
echo 输出文件：
echo %CUT_MP4%
echo %OUTPUT_MP3%

pause