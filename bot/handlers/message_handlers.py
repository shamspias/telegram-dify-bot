"""Message handlers for the bot."""

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from bot.models.schemas import ChatMessage
from bot.services.conversation_manager import ConversationManager
from bot.services.phyxie_service import PhyxieService, PhyxieAPIError
from bot.utils.decorators import typing_action
from bot.utils.helpers import truncate_text

logger = structlog.get_logger(__name__)


class MessageHandlers:
    """Handlers for text messages."""

    def __init__(self, conversation_manager: ConversationManager, phyxie_service: PhyxieService):
        self.conversation_manager = conversation_manager
        self.phyxie_service = phyxie_service

    @typing_action
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or f"user_{user.id}"
        message_text = update.message.text

        # Get or create conversation
        conversation = self.conversation_manager.get_or_create_conversation(user_id, username)

        try:
            # Create chat message
            chat_message = ChatMessage(
                query=message_text,
                user=username,
                conversation_id=conversation.conversation_id  # May be None for first message
            )

            # Send to Phyxie API
            response = await self.phyxie_service.send_message(chat_message)

            # If this was the first message, update conversation ID
            if not conversation.conversation_id and response.conversation_id:
                self.conversation_manager.update_conversation_id(user_id, response.conversation_id)

            # Update conversation stats
            self.conversation_manager.increment_message_count(user_id)

            # Send response to user
            answer = truncate_text(response.answer)
            await update.message.reply_text(answer)

            # Log successful interaction
            logger.info("Message processed successfully",
                        user_id=user_id,
                        conversation_id=response.conversation_id,
                        message_id=response.message_id)

        except PhyxieAPIError as e:
            logger.error("Phyxie API error", error=str(e))
            await update.message.reply_text(
                "❌ Sorry, I couldn't process your message. Please try again."
            )
        except Exception as e:
            logger.error("Unexpected error", error=str(e), exc_info=True)
            await update.message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )

    async def handle_streaming_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages with streaming response."""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or f"user_{user.id}"
        message_text = update.message.text

        # Get or create conversation
        conversation = self.conversation_manager.get_or_create_conversation(user_id, username)

        # Send initial message
        sent_message = await update.message.reply_text("💭 Thinking...")

        try:
            # Create chat message
            chat_message = ChatMessage(
                query=message_text,
                user=username,
                conversation_id=conversation.conversation_id
            )

            # Stream response
            full_answer = ""
            message_id = None
            conversation_id = None

            async for chunk in self.phyxie_service.stream_message(chat_message):
                if chunk.get("event") == "message":
                    answer_chunk = chunk.get("answer", "")
                    full_answer += answer_chunk
                    conversation_id = chunk.get("conversation_id")

                    # Update message periodically
                    if len(full_answer) % 100 == 0:  # Update every 100 chars
                        await sent_message.edit_text(truncate_text(full_answer))

                elif chunk.get("event") == "message_end":
                    message_id = chunk.get("message_id")
                    conversation_id = chunk.get("conversation_id")

                    # If this was the first message, update conversation ID
                    if not conversation.conversation_id and conversation_id:
                        self.conversation_manager.update_conversation_id(user_id, conversation_id)

                    # Update conversation stats
                    self.conversation_manager.increment_message_count(user_id)

            # Final update
            await sent_message.edit_text(truncate_text(full_answer))

            logger.info("Streaming message processed successfully",
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message_id=message_id)

        except PhyxieAPIError as e:
            logger.error("Phyxie API error", error=str(e))
            await sent_message.edit_text(
                "❌ Sorry, I couldn't process your message. Please try again."
            )
        except Exception as e:
            logger.error("Unexpected error", error=str(e), exc_info=True)
            await sent_message.edit_text(
                "❌ An unexpected error occurred. Please try again later."
            )
