@echo off

REM Activate virtual environment if it exists
if exist venv\ (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if .env exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure it.
    exit /b 1
)

REM Run the bot
echo Starting Phyxie Telegram Bot...
python main.py