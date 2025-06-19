"""Service for interacting with Phyxie API."""

import json
import aiohttp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.models.schemas import (
    ChatMessage, PhyxieResponse, FileUploadResponse,
    ResponseMode
)
from config.settings import settings

logger = structlog.get_logger(__name__)


class PhyxieAPIError(Exception):
    """Phyxie API error."""
    pass


class PhyxieService:
    """Service for interacting with Phyxie API."""

    def __init__(self):
        self.base_url = settings.phyxie_api_base_url
        self.api_key = settings.phyxie_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(self, message: ChatMessage) -> PhyxieResponse:
        """Send a message to Phyxie API."""
        url = f"{self.base_url}{settings.chat_messages_endpoint}"

        payload = {
            "query": message.query,
            "user": message.user,
            "inputs": message.inputs,
            "response_mode": message.response_mode.value,
            "auto_generate_name": message.auto_generate_name
        }

        if message.conversation_id:
            payload["conversation_id"] = message.conversation_id

        if message.files:
            payload["files"] = [
                {
                    "type": f.type.value,
                    "transfer_method": f.transfer_method.value,
                    "upload_file_id": f.upload_file_id
                }
                for f in message.files
            ]

        logger.info("Sending message to Phyxie",
                    user=message.user,
                    conversation_id=message.conversation_id)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Phyxie API error",
                                     status=response.status,
                                     error=error_text)
                        raise PhyxieAPIError(f"API error: {response.status} - {error_text}")

                    data = await response.json()
                    return PhyxieResponse(**data)

            except aiohttp.ClientError as e:
                logger.error("Network error", error=str(e))
                raise PhyxieAPIError(f"Network error: {str(e)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_file(self, file_data: bytes, filename: str, user: str) -> FileUploadResponse:
        """Upload a file to Phyxie API."""
        url = f"{self.base_url}{settings.file_upload_endpoint}"

        # Prepare multipart form data
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename=filename)
        data.add_field('user', user)

        # Remove Content-Type header for multipart
        headers = {"Authorization": f"Bearer {self.api_key}"}

        logger.info("Uploading file to Phyxie", filename=filename, user=user)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("File upload error",
                                     status=response.status,
                                     error=error_text)
                        raise PhyxieAPIError(f"File upload error: {response.status} - {error_text}")

                    data = await response.json()
                    return FileUploadResponse(**data)

            except aiohttp.ClientError as e:
                logger.error("Network error during file upload", error=str(e))
                raise PhyxieAPIError(f"Network error: {str(e)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def delete_conversation(self, conversation_id: str, user: str) -> bool:
        """Delete a conversation."""
        url = f"{self.base_url}{settings.conversations_endpoint}/{conversation_id}"

        payload = {"user": user}

        logger.info("Deleting conversation",
                    conversation_id=conversation_id,
                    user=user)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(url, headers=self.headers, json=payload) as response:
                    if response.status == 204:
                        return True
                    elif response.status == 404:
                        logger.warning("Conversation not found",
                                       conversation_id=conversation_id)
                        return True  # Already deleted
                    else:
                        error_text = await response.text()
                        logger.error("Delete conversation error",
                                     status=response.status,
                                     error=error_text)
                        raise PhyxieAPIError(f"Delete error: {response.status} - {error_text}")

            except aiohttp.ClientError as e:
                logger.error("Network error during deletion", error=str(e))
                raise PhyxieAPIError(f"Network error: {str(e)}")

    async def stream_message(self, message: ChatMessage):
        """Send a message and stream the response."""
        url = f"{self.base_url}{settings.chat_messages_endpoint}"
        message.response_mode = ResponseMode.STREAMING

        payload = {
            "query": message.query,
            "user": message.user,
            "inputs": message.inputs,
            "response_mode": message.response_mode.value,
            "auto_generate_name": message.auto_generate_name
        }

        if message.conversation_id:
            payload["conversation_id"] = message.conversation_id

        if message.files:
            payload["files"] = [
                {
                    "type": f.type.value,
                    "transfer_method": f.transfer_method.value,
                    "upload_file_id": f.upload_file_id
                }
                for f in message.files
            ]

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise PhyxieAPIError(f"API error: {response.status} - {error_text}")

                    async for line in response.content:
                        if line:
                            text = line.decode('utf-8').strip()
                            if text.startswith('data: '):
                                data_str = text[6:]  # Remove 'data: ' prefix
                                if data_str:
                                    try:
                                        data = json.loads(data_str)
                                        yield data
                                    except json.JSONDecodeError:
                                        logger.warning("Failed to parse SSE data", data=data_str)

            except aiohttp.ClientError as e:
                logger.error("Network error during streaming", error=str(e))
                raise PhyxieAPIError(f"Network error: {str(e)}")
