"""Data models and schemas."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class ResponseMode(str, Enum):
    """Response modes for Phyxie API."""
    STREAMING = "streaming"
    BLOCKING = "blocking"


class FileType(str, Enum):
    """File types supported by Phyxie."""
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    CUSTOM = "custom"


class TransferMethod(str, Enum):
    """File transfer methods."""
    REMOTE_URL = "remote_url"
    LOCAL_FILE = "local_file"


@dataclass
class FileUpload:
    """File upload data."""
    type: FileType
    transfer_method: TransferMethod
    upload_file_id: Optional[str] = None
    url: Optional[str] = None


@dataclass
class ChatMessage:
    """Chat message data."""
    query: str
    user: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    response_mode: ResponseMode = ResponseMode.BLOCKING
    conversation_id: Optional[str] = None
    files: List[FileUpload] = field(default_factory=list)
    auto_generate_name: bool = True


@dataclass
class UserConversation:
    """User conversation state."""
    user_id: str
    username: str
    conversation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0


@dataclass
class PhyxieResponse:
    """Phyxie API response."""
    event: str
    task_id: str
    id: str
    message_id: str
    conversation_id: str
    mode: str
    answer: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = 0


@dataclass
class FileUploadResponse:
    """File upload response."""
    id: str
    name: str
    size: int
    extension: str
    mime_type: str
    created_by: str
    created_at: int
