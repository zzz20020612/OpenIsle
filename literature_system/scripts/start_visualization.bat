@echo off
setlocal EnableDelayedExpansion

rem 切换到脚本所在目录的上一级（项目根目录）
cd /d "%~dp0\.."

rem 从 config\.env 读取 SEARCH_API_PORT，未找到则默认 8088
set "PORT="
for /f "tokens=2 delims==" %%a in ('findstr /B "SEARCH_API_PORT=" "config\.env"') do set "PORT=%%a"
if not defined PORT set "PORT=8088"

rem 自动打开浏览器
echo 正在打开 http://localhost:%PORT%/
start http://localhost:%PORT%/

rem 启动可视化 API 服务
echo 启动文献可视化服务，端口 %PORT% ...
python code/search/api.py --port %PORT%
