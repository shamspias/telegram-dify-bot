"""Main bot class."""

import structlog
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

from config.settings import settings
from bot.services.conversation_manager import ConversationManager
from bot.services.phyxie_service import PhyxieService
from bot.handlers.command_handlers import CommandHandlers
from bot.handlers.message_handlers import MessageHandlers
from bot.handlers.file_handlers import FileHandlers

logger = structlog.get_logger(__name__)


class PhyxieBot:
    """Main bot class."""

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.conversation_manager = ConversationManager()
        self.phyxie_service = PhyxieService()

        # Initialize handlers
        self.command_handlers = CommandHandlers(
            self.conversation_manager,
            self.phyxie_service
        )
        self.message_handlers = MessageHandlers(
            self.conversation_manager,
            self.phyxie_service
        )
        self.file_handlers = FileHandlers(
            self.conversation_manager,
            self.phyxie_service
        )

        # Build application
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up message handlers."""

        # Command handlers - Create wrapper functions to properly bind self
        async def start_command(update, context):
            return await self.command_handlers.start_command(update, context)

        async def new_command(update, context):
            return await self.command_handlers.new_command(update, context)

        async def clear_command(update, context):
            return await self.command_handlers.clear_command(update, context)

        async def help_command(update, context):
            return await self.command_handlers.help_command(update, context)

        async def handle_photo(update, context):
            return await self.file_handlers.handle_photo(update, context)

        async def handle_document(update, context):
            return await self.file_handlers.handle_document(update, context)

        async def handle_text_message(update, context):
            return await self.message_handlers.handle_text_message(update, context)

        # Register handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("new", new_command))
        self.application.add_handler(CommandHandler("clear", clear_command))
        self.application.add_handler(CommandHandler("help", help_command))

        # Photo handler
        self.application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

        # Document handler
        self.application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        # Text message handler (should be last)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
        )

        # Error handler
        self.application.add_error_handler(self._error_handler)

    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error("Update caused error",
                     error=str(context.error),
                     update=update,
                     exc_info=context.error)

        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )

    async def _set_bot_commands(self):
        """Set bot commands for the menu."""
        commands = [
            BotCommand("start", "Show welcome message"),
            BotCommand("new", "Start a new conversation"),
            BotCommand("clear", "Clear current conversation"),
            BotCommand("help", "Show help message"),
        ]
        await self.application.bot.set_my_commands(commands)

    async def post_init(self, application: Application) -> None:
        """Initialize the bot after application is built."""
        await self._set_bot_commands()
        logger.info("Bot commands set successfully")

    def run(self):
        """Run the bot."""
        logger.info("Starting Phyxie Telegram Bot...")

        # Add post init
        self.application.post_init = self.post_init

        # Initialize bot
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        logger.info("Bot stopped")
