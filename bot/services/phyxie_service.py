"""Service for interacting with the Phyxie Service-API."""

from __future__ import annotations

import json
from typing import AsyncIterator, Dict, List

import aiohttp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from bot.utils.helpers import get_mime_type

from bot.models.schemas import (
    ChatMessage,
    FileUploadResponse,
    PhyxieResponse,
    ResponseMode,
    TransferMethod,
)
from config.settings import settings

logger = structlog.get_logger(__name__)


class PhyxieAPIError(Exception):
    """Raised for any non-network error returned by the Phyxie Service-API."""


class PhyxieService:
    """Thin async client around the Phyxie Service-API."""

    def __init__(self) -> None:
        self.base_url: str = settings.phyxie_api_base_url.rstrip("/")
        self.api_key: str = settings.phyxie_api_key
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ----------------------------------------------------------------- #
    #  Helpers                                                          #
    # ----------------------------------------------------------------- #

    def _build_files_section(self, files: List) -> List[Dict]:
        """
        Build the JSON list for the `files` parameter.

        • Local file that you already uploaded  →  transfer_method = local_file
        • Public URL                            →  transfer_method = remote_url
        """
        file_payload: List[Dict] = []

        for f in files:
            item: Dict[str, str] = {"type": f.type.value}

            if f.upload_file_id:  # ← local file already on Phyxie
                item.update(
                    {
                        "transfer_method": TransferMethod.LOCAL_FILE.value,
                        "upload_file_id": f.upload_file_id,
                    }
                )

            elif f.url:  # ← remote image/document URL
                item.update(
                    {
                        "transfer_method": TransferMethod.REMOTE_URL.value,
                        "url": f.url,
                    }
                )

            file_payload.append(item)

        return file_payload

    async def _post_json(self, url: str, payload: Dict) -> Dict:
        """POST JSON and always return body (or raise PhyxieAPIError)."""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    logger.error("Phyxie API error", status=resp.status, body=text)
                    raise PhyxieAPIError(f"{resp.status}: {text}")

                return json.loads(text)

    # --------------------------------------------------------------------- #
    #  Chat endpoints                                                       #
    # --------------------------------------------------------------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(self, message: ChatMessage) -> PhyxieResponse:
        """Blocking mode request to `/chat-messages`."""
        url = f"{self.base_url}{settings.chat_messages_endpoint}"

        payload: Dict = {
            "query": message.query,
            "user": message.user,
            "inputs": message.inputs,
            "response_mode": message.response_mode.value,
            "auto_generate_name": message.auto_generate_name,
        }

        if message.conversation_id:
            payload["conversation_id"] = message.conversation_id

        if message.files:
            payload["files"] = self._build_files_section(message.files)

        logger.info("Sending message to Phyxie", user=message.user, conversation_id=message.conversation_id)

        data = await self._post_json(url, payload)
        return PhyxieResponse(**data)

    # ------------------------------------------------------------------ #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def stream_message(self, message: ChatMessage) -> AsyncIterator[Dict]:
        """Send message in streaming mode and yield SSE chunks."""
        url = f"{self.base_url}{settings.chat_messages_endpoint}"
        message.response_mode = ResponseMode.STREAMING

        payload: Dict = {
            "query": message.query,
            "user": message.user,
            "inputs": message.inputs,
            "response_mode": message.response_mode.value,
            "auto_generate_name": message.auto_generate_name,
        }

        if message.conversation_id:
            payload["conversation_id"] = message.conversation_id

        if message.files:
            payload["files"] = self._build_files_section(message.files)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, json=payload) as resp:
                    # If the handshake itself fails, read body for details
                    if resp.status >= 400:
                        body = await resp.text()
                        logger.error("Phyxie API error", status=resp.status, body=body)
                        raise PhyxieAPIError(f"{resp.status}: {body}")

                    async for line in resp.content:
                        if not line:
                            continue
                        text = line.decode().strip()
                        if not text.startswith("data: "):
                            continue
                        chunk = text[6:]
                        if chunk:
                            yield json.loads(chunk)

            except aiohttp.ClientError as e:
                logger.error("Network error during streaming", error=str(e))
                raise PhyxieAPIError(f"Network error: {str(e)}") from e

    # --------------------------------------------------------------------- #
    #  File upload                                                          #
    # --------------------------------------------------------------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def upload_file(self, file_data: bytes, filename: str, user: str) -> FileUploadResponse:
        """Upload a file to Phyxie API and get an upload_file_id."""
        url = f"{self.base_url}{settings.file_upload_endpoint}"

        mime_type = get_mime_type(filename)  # ← new

        form = aiohttp.FormData()
        form.add_field(
            "file",
            file_data,
            filename=filename,
            content_type=mime_type  # ← new
        )
        form.add_field("user", user)

        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    logger.error("File upload error", status=resp.status, body=body)
                    raise PhyxieAPIError(f"{resp.status}: {body}")

                return FileUploadResponse(**json.loads(body))

    # --------------------------------------------------------------------- #
    #  Conversation deletion                                                #
    # --------------------------------------------------------------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def delete_conversation(self, conversation_id: str, user: str) -> bool:
        """DELETE `/conversations/{conversation_id}`."""
        url = f"{self.base_url}{settings.conversations_endpoint}/{conversation_id}"
        payload = {"user": user}

        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self.headers, json=payload) as resp:
                body = await resp.text()

                match resp.status:
                    case 204:
                        return True
                    case 404:
                        logger.warning("Conversation not found on server", conversation_id=conversation_id)
                        return True
                    case _ if resp.status >= 400:
                        logger.error("Delete conversation error", status=resp.status, body=body)
                        raise PhyxieAPIError(f"{resp.status}: {body}")

        return False
