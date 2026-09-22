@echo off
cd /d "E:\web\tool bot\đoanxem"

:loop
"C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe" src\bot.py >> bot_run.log 2>&1
timeout /t 5 /nobreak >nul
goto loop
