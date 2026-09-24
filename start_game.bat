@echo off
rem Sticker Beauty Shop launcher: local server (game + neural voices) then Edge fullscreen app window.
cd /d "%~dp0"
start "" pyw -3.11 server.py
ping -n 3 127.0.0.1 >nul
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --user-data-dir="%LOCALAPPDATA%\StickerShop\edge" --app=http://127.0.0.1:8765/index.html --start-fullscreen --no-first-run --no-default-browser-check --autoplay-policy=no-user-gesture-required
