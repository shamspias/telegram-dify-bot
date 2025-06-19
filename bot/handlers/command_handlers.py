"""Command handlers for the bot."""

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.decorators import log_command
from bot.utils.helpers import format_welcome_message, format_help_message
from bot.services.conversation_manager import ConversationManager
from bot.services.phyxie_service import PhyxieService

logger = structlog.get_logger(__name__)


class CommandHandlers:
    """Handlers for bot commands."""

    def __init__(self, conversation_manager: ConversationManager, phyxie_service: PhyxieService):
        self.conversation_manager = conversation_manager
        self.phyxie_service = phyxie_service

    @log_command
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        username = user.username or f"user_{user.id}"

        welcome_message = format_welcome_message(username)
        await update.message.reply_text(welcome_message)

    @log_command
    async def new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /new command - Start a new conversation."""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or f"user_{user.id}"

        # Create new conversation
        conversation = self.conversation_manager.create_new_conversation(user_id, username)

        await update.message.reply_text(
            f"✨ New conversation started!\n\n"
            f"Send me your first message to begin chatting.\n"
            f"You can send text, images, or documents."
        )

    @log_command
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /clear command - Clear current conversation."""
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or f"user_{user.id}"

        # Get current conversation
        current_conversation = self.conversation_manager.get_conversation(user_id)

        if current_conversation and current_conversation.conversation_id:
            try:
                # Delete conversation from API
                await self.phyxie_service.delete_conversation(
                    current_conversation.conversation_id,
                    username
                )

                # Clear local conversation
                self.conversation_manager.clear_conversation(user_id)

                # Create new conversation placeholder
                new_conversation = self.conversation_manager.create_new_conversation(user_id, username)

                await update.message.reply_text(
                    f"🗑️ Previous conversation cleared!\n\n"
                    f"✨ Ready to start fresh!\n"
                    f"Send me a message to begin a new conversation."
                )
            except Exception as e:
                logger.error("Failed to clear conversation", error=str(e))
                await update.message.reply_text(
                    "❌ Failed to clear conversation. Please try again."
                )
        else:
            # No existing conversation, just create new one
            new_conversation = self.conversation_manager.create_new_conversation(user_id, username)
            await update.message.reply_text(
                f"✨ Ready to start!\n"
                f"Send me a message to begin a new conversation."
            )

    @log_command
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = format_help_message()
        await update.message.reply_text(help_message, parse_mode="MarkdownV2")
