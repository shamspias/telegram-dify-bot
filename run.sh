#!/bin/bash

set -e  # Exit on error

# Preferred virtual environment directory name
VENV_DIR="venv"

# List of possible virtual environment directory names
VENV_CANDIDATES=("venv" ".venv" "virtualenv" ".virtualenv")

# Function to create a virtual environment
create_virtualenv() {
    echo "No existing virtual environment found. Creating one in '$VENV_DIR'..."
    python3 -m venv "$VENV_DIR"
}

# Look for existing virtual environments
for dir in "${VENV_CANDIDATES[@]}"; do
    if [ -d "$dir" ]; then
        VENV_DIR="$dir"
        break
    fi
done

# Create virtual environment if none was found
if [ ! -d "$VENV_DIR" ]; then
    create_virtualenv
fi

# Activate the virtual environment
echo "Activating virtual environment in '$VENV_DIR'..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Skipping dependency installation."
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Run the bot
echo "Starting Phyxie Telegram Bot..."
python main.py
