"""Conversation manager for handling user sessions."""

import uuid
import structlog
from typing import Dict, Optional
from datetime import datetime

from bot.models.schemas import UserConversation

logger = structlog.get_logger(__name__)


class ConversationManager:
    """Manages user conversations and sessions."""

    def __init__(self):
        self._conversations: Dict[str, UserConversation] = {}

    def get_or_create_conversation(self, user_id: str, username: str) -> UserConversation:
        """Get existing conversation or create a new one."""
        if user_id not in self._conversations:
            conversation = UserConversation(
                user_id=user_id,
                username=username,
                conversation_id=None  # Let API create the conversation
            )
            self._conversations[user_id] = conversation
            logger.info("Created new conversation placeholder",
                        user_id=user_id)

        return self._conversations[user_id]

    def create_new_conversation(self, user_id: str, username: str) -> UserConversation:
        """Create a new conversation for the user."""
        conversation = UserConversation(
            user_id=user_id,
            username=username,
            conversation_id=None  # Let API create the conversation
        )
        self._conversations[user_id] = conversation
        logger.info("Created new conversation placeholder",
                    user_id=user_id)
        return conversation

    def update_conversation_id(self, user_id: str, conversation_id: str) -> None:
        """Update conversation ID after API creates it."""
        if user_id in self._conversations:
            self._conversations[user_id].conversation_id = conversation_id
            logger.info("Updated conversation ID",
                        user_id=user_id,
                        conversation_id=conversation_id)

    def get_conversation(self, user_id: str) -> Optional[UserConversation]:
        """Get user's current conversation."""
        return self._conversations.get(user_id)

    def clear_conversation(self, user_id: str) -> None:
        """Clear user's conversation."""
        if user_id in self._conversations:
            old_conversation_id = self._conversations[user_id].conversation_id
            logger.info("Clearing conversation",
                        user_id=user_id,
                        conversation_id=old_conversation_id)
            del self._conversations[user_id]

    def increment_message_count(self, user_id: str) -> None:
        """Increment message count for a conversation."""
        if user_id in self._conversations:
            self._conversations[user_id].message_count += 1

    @staticmethod
    def _generate_conversation_id() -> str:
        """Generate a unique conversation ID."""
        return str(uuid.uuid4())

    def get_all_conversations(self) -> Dict[str, UserConversation]:
        """Get all active conversations."""
        return self._conversations.copy()

    def get_stats(self) -> Dict:
        """Get conversation statistics."""
        total_conversations = len(self._conversations)
        total_messages = sum(conv.message_count for conv in self._conversations.values())

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "active_users": list(self._conversations.keys())
        }
