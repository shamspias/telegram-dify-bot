"""Helper functions for the bot."""

import os
import mimetypes
from typing import Tuple, Optional
from pathlib import Path

from config.settings import settings
from bot.models.schemas import FileType


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return Path(filename).suffix[1:].lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    extension = get_file_extension(filename)
    return extension in settings.allowed_file_extensions


def get_file_type(filename: str) -> FileType:
    """Determine file type from filename."""
    extension = get_file_extension(filename)

    if extension in settings.image_extensions:
        return FileType.IMAGE
    elif extension in settings.document_extensions:
        return FileType.DOCUMENT
    else:
        return FileType.CUSTOM


def validate_file_size(file_size: int) -> Tuple[bool, Optional[str]]:
    """Validate file size."""
    if file_size > settings.max_file_size_bytes:
        size_mb = file_size / (1024 * 1024)
        return False, f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({settings.max_file_size_mb}MB)"
    return True, None


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    escape_chars = '_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_welcome_message(username: str) -> str:
    """Format welcome message."""
    return (
        f"👋 Welcome to Phyxie Bot, {username}!\n\n"
        "I'm here to help you chat with the Phyxie AI assistant.\n\n"
        "Available commands:\n"
        "• /new - Start a new conversation\n"
        "• /clear - Clear current conversation and start fresh\n"
        "• /help - Show this help message\n\n"
        "You can send me text messages, images, or documents, and I'll process them with AI!\n\n"
        "Use /new to start your first conversation."
    )


def format_help_message() -> str:
    """Format help message."""
    return (
        "🤖 *Phyxie Bot Help*\n\n"
        "*Available Commands:*\n"
        "• `/start` \\- Show welcome message\n"
        "• `/new` \\- Start a new conversation\n"
        "• `/clear` \\- Delete current conversation and start fresh\n"
        "• `/help` \\- Show this help message\n\n"
        "*Features:*\n"
        "• Send text messages for AI responses\n"
        "• Upload images \\(JPG, PNG, GIF, etc\\.\\)\n"
        "• Upload documents \\(PDF, DOCX, XLSX, etc\\.\\)\n"
        f"• Maximum file size: {settings.max_file_size_mb}MB\n\n"
        "*Tips:*\n"
        "• Each conversation maintains context\n"
        "• Use `/new` to start a fresh topic\n"
        "• Use `/clear` to completely reset\n"
        "• Your username is used as your unique ID"
    )
