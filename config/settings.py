"""Configuration settings for the bot."""

import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import validator
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Telegram Settings
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Phyxie API Settings
    phyxie_api_base_url: str = os.getenv("PHYXIE_API_BASE_URL", "https://dify.com/v1")
    phyxie_api_key: str = os.getenv("PHYXIE_API_KEY", "")

    # Bot Configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))
    allowed_file_extensions: List[str] = os.getenv(
        "ALLOWED_FILE_EXTENSIONS",
        "jpg,jpeg,png,gif,webp,svg,pdf,txt,md,markdown,html,xlsx,xls,docx,csv,eml,msg,pptx,ppt,xml,epub"
    ).split(",")

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    logs_dir: Path = base_dir / "logs"

    # API Endpoints
    chat_messages_endpoint: str = "/chat-messages"
    file_upload_endpoint: str = "/files/upload"
    conversations_endpoint: str = "/conversations"

    # File type mappings
    image_extensions: List[str] = ["jpg", "jpeg", "png", "gif", "webp", "svg"]
    document_extensions: List[str] = ["pdf", "txt", "md", "markdown", "html", "xlsx", "xls", "docx", "csv", "eml",
                                      "msg", "pptx", "ppt", "xml", "epub"]

    @validator("telegram_bot_token")
    def validate_telegram_token(cls, v):
        if not v:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        return v

    @validator("phyxie_api_key")
    def validate_api_key(cls, v):
        if not v:
            raise ValueError("PHYXIE_API_KEY is required")
        return v

    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

    class Config:
        """Pydantic config."""
        case_sensitive = False


# Create settings instance
settings = Settings()
