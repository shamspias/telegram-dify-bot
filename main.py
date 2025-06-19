"""Main entry point for the bot."""

import logging
import structlog

from bot.bot import PhyxieBot
from config.settings import settings


def setup_logging():
    """Configure logging."""
    # Create logs directory
    settings.logs_dir.mkdir(exist_ok=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(settings.logs_dir / "bot.log")
        ]
    )

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)


def main():
    """Main function."""
    setup_logging()

    logger = structlog.get_logger(__name__)
    logger.info("Starting Phyxie Telegram Bot",
                api_base_url=settings.phyxie_api_base_url,
                log_level=settings.log_level)

    try:
        # Create and run bot
        bot = PhyxieBot()

        # Run the bot
        bot.run()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Bot crashed", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    main()
