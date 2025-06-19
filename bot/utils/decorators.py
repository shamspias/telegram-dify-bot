"""Decorators for the bot."""

import functools
import structlog
from telegram import Update
from telegram.ext import ContextTypes

logger = structlog.get_logger(__name__)


def log_command(func):
    """Log command execution."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        command = update.message.text.split()[0] if update.message else "Unknown"

        logger.info("Command executed",
                    command=command,
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name)

        try:
            return await func(update, context)
        except Exception as e:
            logger.error("Command error",
                         command=command,
                         user_id=user.id,
                         error=str(e),
                         exc_info=True)

            await update.message.reply_text(
                "❌ An error occurred while processing your request. Please try again later."
            )

    return wrapper


def require_conversation(func):
    """Ensure user has an active conversation."""

    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        conversation = self.conversation_manager.get_conversation(str(user.id))

        if not conversation:
            await update.message.reply_text(
                "❌ No active conversation found. Please use /new to start a new conversation."
            )
            return

        return await func(self, update, context)

    return wrapper


def typing_action(func):
    """Send typing action while processing."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_chat_action("typing")
        return await func(update, context)

    return wrapper
