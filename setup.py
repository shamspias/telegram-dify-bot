#!/usr/bin/env python
"""Setup script for initial bot configuration."""

import os
import sys
import shutil
from pathlib import Path


def main():
    """Setup the bot environment."""
    print("🤖 Phyxie Telegram Bot Setup")
    print("=" * 40)

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required!")
        sys.exit(1)

    print(f"✅ Python {sys.version.split()[0]} detected")

    # Create necessary directories
    directories = ["logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}/")

    # Copy .env.example to .env if not exists
    if not Path(".env").exists():
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from .env.example")
            print("⚠️  Please edit .env and add your credentials!")
        else:
            print("❌ Error: .env.example not found!")
            sys.exit(1)
    else:
        print("✅ .env file already exists")

    # Check if virtual environment exists
    if not Path("venv").exists():
        print("\n⚠️  Virtual environment not found!")
        print("Run the following commands to create it:")
        print("  python -m venv venv")
        if os.name == 'nt':  # Windows
            print("  venv\\Scripts\\activate")
        else:  # Unix/Linux/MacOS
            print("  source venv/bin/activate")
        print("  pip install -r requirements.txt")
    else:
        print("✅ Virtual environment found")

    print("\n✨ Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your credentials")
    print("2. Activate virtual environment")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Run the bot: python main.py")


if __name__ == "__main__":
    main()
