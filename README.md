# Dify Telegram Bot

A sophisticated Telegram bot that integrates with the Phyxie AI assistant API from Dify, providing conversational AI capabilities with file upload support.

## Features

- 🤖 **AI-Powered Conversations**: Chat with the Phyxie AI assistant
- 📁 **File Support**: Upload images and documents for AI analysis
- 💬 **Conversation Management**: Create, manage, and clear conversations
- 🔐 **User Isolation**: Each Telegram user has their own conversation context
- 📊 **Multiple File Types**: Support for images (JPG, PNG, etc.) and documents (PDF, DOCX, XLSX, etc.)
- ⚡ **Async Operations**: Built with async/await for optimal performance

## Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Phyxie API Key and Endpoint

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/shamspias/telegram-dify-bot.git
cd phyxie-telegram-bot
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
PHYXIE_API_KEY=your_phyxie_api_key_here
PHYXIE_API_BASE_URL=http://agents.algolyzerlab.com/v1
```

## Usage

### Starting the Bot

```bash
python main.py
```

### Bot Commands

- `/start` - Show welcome message
- `/new` - Start a new conversation
- `/clear` - Delete current conversation and start fresh
- `/help` - Show help message

### Sending Messages

1. Start a conversation with `/new`
2. Send text messages for AI responses
3. Upload images or documents with optional captions
4. Use `/clear` to reset the conversation context

### File Upload

The bot supports uploading:
- **Images**: JPG, JPEG, PNG, GIF, WEBP, SVG
- **Documents**: PDF, TXT, MD, HTML, XLSX, XLS, DOCX, CSV, PPT, PPTX, XML, EPUB, and more

Maximum file size: 15MB (configurable)

## Project Structure

```
dify-telegram-bot/
├── bot/
│   ├── handlers/          # Command, message, and file handlers
│   ├── services/          # API and conversation management
│   ├── models/            # Data models and schemas
│   └── utils/             # Helper functions and decorators
├── config/                # Configuration settings
├── logs/                  # Log files
└── main.py               # Entry point
```

## Configuration

Additional settings in `.env`:

```env
LOG_LEVEL=INFO                    # Logging level (DEBUG, INFO, WARNING, ERROR)
MAX_FILE_SIZE_MB=15              # Maximum file size in MB
ALLOWED_FILE_EXTENSIONS=jpg,jpeg,png,pdf,docx,xlsx  # Comma-separated list
```

## Architecture

The bot follows a clean architecture pattern:

- **Handlers**: Process Telegram updates (commands, messages, files)
- **Services**: Handle business logic and API communication
- **Models**: Define data structures and schemas
- **Utils**: Provide helper functions and decorators

### Key Components

1. **ConversationManager**: Manages user sessions and conversation states
2. **PhyxieService**: Handles API communication with retry logic
3. **CommandHandlers**: Process bot commands
4. **MessageHandlers**: Handle text messages
5. **FileHandlers**: Process file uploads

## Error Handling

The bot includes comprehensive error handling:
- Retry logic for API calls
- User-friendly error messages
- Detailed logging for debugging
- Graceful degradation on failures

## Logging

Logs are stored in the `logs/` directory with:
- Console output for development
- File output for production
- Structured logging with contextual information

## Security Considerations

- API keys are stored in environment variables
- User isolation ensures privacy
- File validation prevents malicious uploads
- Size limits protect against resource exhaustion

## Development

### Adding New Features

1. Create new handlers in `bot/handlers/`
2. Add service methods in `bot/services/`
3. Define models in `bot/models/schemas.py`
4. Register handlers in `bot/bot.py`

### Testing

```python
# Run with debug logging
LOG_LEVEL=DEBUG python main.py
```

## Troubleshooting

### Common Issues

1. **"TELEGRAM_BOT_TOKEN is required"**: Ensure `.env` file exists with valid token
2. **"API error: 401"**: Check your Phyxie API key
3. **File upload fails**: Verify file size and type restrictions
4. **Connection errors**: Check network and API endpoint

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the logs in `logs/bot.log`
- Review error messages in the console
- Ensure all environment variables are set correctly

## Acknowledgments

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Powered by [Algolyzer Lab](https://algolyzerlab.com)
- Uses async/await for optimal performance