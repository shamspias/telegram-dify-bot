"""File handlers for the bot."""

import io
import structlog
from telegram import Update, PhotoSize, Document
from telegram.ext import ContextTypes

from bot.models.schemas import ChatMessage, FileUpload, TransferMethod
from bot.services.conversation_manager import ConversationManager
from bot.services.phyxie_service import PhyxieService, PhyxieAPIError
from bot.utils.decorators import typing_action
from config.settings import settings
from bot.utils.helpers import (
    get_file_extension, is_allowed_file, get_file_type,
    validate_file_size, format_file_size
)

logger = structlog.get_logger(__name__)


class FileHandlers:
    """Handlers for file uploads."""

    def __init__(self, conversation_manager: ConversationManager, phyxie_service: PhyxieService):
        self.conversation_manager = conversation_manager
        self.phyxie_service = phyxie_service

    @typing_action
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo uploads."""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or f"user_{user.id}"

        # Get or create conversation
        conversation = self.conversation_manager.get_or_create_conversation(user_id, username)

        # Get the largest photo
        photo: PhotoSize = update.message.photo[-1]
        caption = update.message.caption or "Analyze this image"

        try:
            # Download photo
            file = await context.bot.get_file(photo.file_id)
            file_data = io.BytesIO()
            await file.download_to_memory(file_data)
            file_data.seek(0)

            # Generate filename
            filename = f"photo_{photo.file_unique_id}.jpg"

            # Upload to Phyxie
            await update.message.reply_text("📤 Uploading image...")

            upload_response = await self.phyxie_service.upload_file(
                file_data.read(),
                filename,
                username
            )

            # Create file upload object
            file_upload = FileUpload(
                type=get_file_type(filename),
                transfer_method=TransferMethod.LOCAL_FILE,
                upload_file_id=upload_response.id
            )

            # Send message with file
            chat_message = ChatMessage(
                query=caption,
                user=username,
                conversation_id=conversation.conversation_id,
                files=[file_upload]
            )

            response = await self.phyxie_service.send_message(chat_message)

            # If this was the first message, update conversation ID
            if not conversation.conversation_id and response.conversation_id:
                self.conversation_manager.update_conversation_id(user_id, response.conversation_id)

            # Update conversation stats
            self.conversation_manager.increment_message_count(user_id)

            # Send response
            await update.message.reply_text(response.answer)

            logger.info("Photo processed successfully",
                        user_id=user_id,
                        filename=filename,
                        file_id=upload_response.id)

        except PhyxieAPIError as e:
            logger.error("Failed to process photo", error=str(e))
            await update.message.reply_text(
                "❌ Failed to process the image. Please try again."
            )
        except Exception as e:
            logger.error("Unexpected error", error=str(e), exc_info=True)
            await update.message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )

    @typing_action
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle document uploads."""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or f"user_{user.id}"

        # Get or create conversation
        conversation = self.conversation_manager.get_or_create_conversation(user_id, username)

        document: Document = update.message.document
        caption = update.message.caption or f"Analyze this {document.file_name}"

        # Validate file
        if not is_allowed_file(document.file_name):
            extension = get_file_extension(document.file_name)
            await update.message.reply_text(
                f"❌ File type '.{extension}' is not supported.\n"
                f"Supported types: {', '.join(settings.allowed_file_extensions)}"
            )
            return

        # Validate file size
        is_valid, error_msg = validate_file_size(document.file_size)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return

        try:
            # Download document
            file = await context.bot.get_file(document.file_id)
            file_data = io.BytesIO()
            await file.download_to_memory(file_data)
            file_data.seek(0)

            # Upload to Phyxie
            await update.message.reply_text(
                f"📤 Uploading {document.file_name} ({format_file_size(document.file_size)})..."
            )

            upload_response = await self.phyxie_service.upload_file(
                file_data.read(),
                document.file_name,
                username
            )

            # Create file upload object
            file_upload = FileUpload(
                type=get_file_type(document.file_name),
                transfer_method=TransferMethod.LOCAL_FILE,
                upload_file_id=upload_response.id
            )

            # Send message with file
            chat_message = ChatMessage(
                query=caption,
                user=username,
                conversation_id=conversation.conversation_id,
                files=[file_upload]
            )

            response = await self.phyxie_service.send_message(chat_message)

            # If this was the first message, update conversation ID
            if not conversation.conversation_id and response.conversation_id:
                self.conversation_manager.update_conversation_id(user_id, response.conversation_id)

            # Update conversation stats
            self.conversation_manager.increment_message_count(user_id)

            # Send response
            await update.message.reply_text(response.answer)

            logger.info("Document processed successfully",
                        user_id=user_id,
                        filename=document.file_name,
                        file_id=upload_response.id,
                        file_size=document.file_size)

        except PhyxieAPIError as e:
            logger.error("Failed to process document", error=str(e))
            await update.message.reply_text(
                "❌ Failed to process the document. Please try again."
            )
        except Exception as e:
            logger.error("Unexpected error", error=str(e), exc_info=True)
            await update.message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )
