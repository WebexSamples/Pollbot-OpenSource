# Pollbot-OpenSource

This is an open source version of [Pollbot](https://apphub.webex.com/applications/pollbot-cisco-systems-12150-78220-99857) that can be found on the Webex AppHub. Feel free to rename it and modify it to fit your needs.

## 🎯 Overview

Pollbot-OpenSource is a comprehensive polling bot for Webex Teams that enables users to create interactive polls, surveys, and collect feedback within their Webex spaces. Built with Python and Tornado, it features both text-based commands and rich Adaptive Cards for an enhanced user experience.

## ✨ Key Features

- **Interactive Polling**: Create polls with multiple choice questions
- **Adaptive Cards**: Modern, interactive UI with buttons and forms
- **Real-time Results**: Live poll results and status updates
- **Privacy Controls**: Public or private poll results
- **Multiple Question Types**: Single and multiple question polls
- **Time-based Polls**: Set poll duration and automatic expiration
- **Comprehensive Commands**: Both typed commands and card-based interactions
- **MongoDB Integration**: Persistent poll storage and analytics
- **Webhook Security**: Secure webhook validation with secrets

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- MongoDB database
- Webex Teams bot account
- Public web server or ngrok for webhooks

### Bot Setup

To create your own Webex bot to use within this app see https://developer.webex.com/docs/bots.

### Environment Configuration

In order to use this app you will need to create a `.env` file with required environment variables. A [sample](example.env) has been provided showing what the variables are that will need values provided. If you wish to handle the environment variables differently you can comment out or remove the import for dotenv, located [here](pollbot/src/settings.py#L24).

### Required Webhooks

Three [webhooks](https://developer.webex.com/docs/webhooks) are required and it is recommended to include a webhook secret when creating them.

See https://developer.webex.com/docs/webhooks for how to create webhooks. Be sure to use your bot token to create the webhooks.

The secret defined when creating the webhooks will need to be included in the environment variables.

1. **"resource": "messages", "event": "created"** - pointed to the root of where you're hosting the app.  
   Example: `https://example.com`

2. **"resource": "attachmentActions", "event": "created"** - pointed to /cards.  
   Example: `https://example.com/cards`

3. **"resource": "memberships", "event": "all"** - pointed to /memberships.  
   Example: `https://example.com/memberships`

### Support Link Configuration

In the following cards, there is a place where you can provide your own support link so your users can contact you with any issues that may occur.

- [edit_card.json](pollbot/src/cards/edit_card.json#L36)
- [help_direct_card.json](pollbot/src/cards/help_direct_card.json#L43)
- [help_active_card.json](pollbot/src/cards/help_active_card.json#L75)
- [help_group_card.json](pollbot/src/cards/help_group_card.json#L48)
- [setup_card.json](pollbot/src/cards/setup_card.json#L135)

## 📦 Install and Run

### Manual Installation

**Clone the repository:**
```bash
git clone https://github.com/WebexSamples/Pollbot-OpenSource.git
```

**Install dependencies:**

To install the required modules you can use the [requirements.txt](requirements.txt) file using pip or pip3.

```bash
pip3 install -r requirements.txt
```

**Configure environment variables:**

Make any changes you wish to make to the code and add your environment variables. You can rename the `example.env` file to `.env` and supply your environment variables in that file.

**Run the application:**

Run the app using the following command in terminal:
```bash
python3 pollbot.py
```

### Docker Installation

An example [Dockerfile](pollbot/Dockerfile) has been provided as well. After editing the Dockerfile and providing your custom bot and DB info you can build the Docker image and run it using the following Docker commands.

**Build the Docker image:**
```bash
docker build -f pollbot/Dockerfile -t pollbot-opensource .
```
You can replace `pollbot-opensource` with whatever name you want.

**Run the Docker container:**
```bash
docker run -p 10060:10060 -i -t pollbot-opensource
```
If you change the port number you'll need to update it in the Dockerfile as well and rebuild the image.

## 📁 Project Structure

```
Pollbot-OpenSource/
├── pollbot.py                      # Main application entry point
├── pollbot/                        # Core application package
│   ├── src/                        # Source code
│   │   ├── settings.py            # Configuration settings
│   │   ├── basehandler.py         # Base request handlers
│   │   ├── spark.py               # Webex API integration
│   │   ├── mongo_db_controller.py # Database operations
│   │   ├── card_builder.py        # Adaptive Card generation
│   │   ├── app_helper.py          # Application utilities
│   │   ├── alive.py               # Health check endpoints
│   │   └── cards/                 # Adaptive Card templates
│   │       ├── create_card.json
│   │       ├── help_active_card.json
│   │       ├── help_direct_card.json
│   │       ├── help_group_card.json
│   │       ├── results_card.json
│   │       ├── edit_card.json
│   │       ├── answer_card.json
│   │       └── setup_card.json
│   └── Dockerfile                 # Docker configuration
├── requirements.txt               # Python dependencies
├── example.env                    # Environment variables template
└── README.md                      # This file
```

## 🔧 Dependencies

The application requires the following Python packages:

```
inflect                    # Natural language processing for numbers
pymongo==3.10.1           # MongoDB driver
pymongo[srv]              # MongoDB SRV record support
tornado==4.5.2            # Web framework
requests                  # HTTP library
requests-toolbelt         # HTTP utilities
python-dotenv            # Environment variable management
```

## ⚙️ Configuration

### Environment Variables

The application uses the following environment variables:

**Bot Configuration:**
- `MY_POLLBOT_TOKEN`: Your Webex bot access token
- `MY_POLLBOT_NAMES`: Bot names (comma-separated)
- `MY_POLLBOT_PORT`: Port number for the application
- `MY_POLLBOT_ID`: Bot ID from Webex
- `MY_SECRET_PHRASE`: Webhook secret for validation

**Database Configuration:**
- `POLLBOT_MONGO_DB_URI`: MongoDB connection string
- `POLLBOT_MONGO_DB_NAME`: Database name
- `POLLBOT_MONGO_COLLECTION_NAME`: Collection name for polls

**Application Settings:**
- `POLLBOT_DEFAULT_DURATION`: Default poll duration in minutes
- `POLLBOT_LOOP_SLEEP_SECONDS`: Background task sleep interval
- `METRICS_BOT_ID`: Metrics collection bot ID

**Card File Paths:**
- `POLLBOT_CREATE_CARD_FILE`: Path to create poll card
- `POLLBOT_HELP_ACTIVE_CARD_FILE`: Path to help card for active polls
- `POLLBOT_HELP_GROUP_CARD_FILE`: Path to group help card
- `POLLBOT_HELP_DIRECT_CARD_FILE`: Path to direct help card
- `POLLBOT_RESULTS_CARD_FILE`: Path to results card
- `POLLBOT_EDIT_CARD_FILE`: Path to edit poll card
- `POLLBOT_ANSWER_CARD_FILE`: Path to answer card
- `POLLBOT_OPTIONS_CARD_FILE`: Path to additional options card
- `POLLBOT_SETUP_CARD_FILE`: Path to setup card

## 🎮 Usage

### Text Commands

**Basic Commands:**
- `@pollbot help` - Show help information
- `@pollbot create poll` - Create a new poll using cards
- `@pollbot results` - View current poll results
- `@pollbot stop` - Stop the current poll
- `@pollbot edit` - Edit poll settings

**Advanced Commands:**
- `@pollbot create What's your favorite color?; Red; Blue; Green` - Create poll with typed command
- `@pollbot public` - Make poll results public
- `@pollbot private` - Make poll results private
- `@pollbot duration 60` - Set poll duration to 60 minutes

### Card-Based Interactions

The bot provides rich interactive cards for:
- **Poll Creation**: Step-by-step poll setup
- **Answer Selection**: Multiple choice answers
- **Results Display**: Real-time poll results
- **Poll Management**: Edit and control poll settings

### Poll Features

**Question Types:**
- Single question polls
- Multiple question polls
- Anonymous voting options
- Multi-answer selection

**Privacy Options:**
- Public results (visible to all)
- Private results (visible to creator only)
- Anonymous voting

**Time Controls:**
- Set custom duration
- Automatic poll expiration
- Real-time countdown

## 🏗️ Architecture

### Core Components

**Main Application (pollbot.py):**
- Tornado web server setup
- Route configuration
- Request handling coordination

**Request Handlers:**
- `MainHandler`: Processes incoming messages
- `CardsHandler`: Handles Adaptive Card interactions
- `CustomMembershipsHandler`: Manages space memberships
- `AliveHandler`: Health check endpoints

**Data Layer:**
- `MongoController`: Database operations
- `MetricsDB`: Analytics and usage tracking
- `Settings`: Configuration management

**Business Logic:**
- `AppHelper`: Application utilities and background tasks
- `CardBuilder`: Adaptive Card generation
- `Spark`: Webex API integration

### Database Schema

**Active Polls Collection:**
```json
{
  "room_id": "string",
  "creator_id": "string",
  "creator_name": "string",
  "questions": [
    {
      "question": "string",
      "answers": ["string"],
      "responses": {}
    }
  ],
  "created_date": "datetime",
  "duration": "integer",
  "private": "boolean",
  "anonymous": "boolean"
}
```

## 🔐 Security

### Webhook Validation

The application validates incoming webhooks using HMAC-SHA1 signatures:

```python
secret_equal = Spark.compare_secret(
    self.request.body, 
    self.request.headers.get('X-Spark-Signature'), 
    Settings.secret_phrase
)
```

### Bot Message Filtering

Automatically filters out messages from other bots:

```python
if webhook['data']['personEmail'].endswith('@sparkbot.io') or 
   webhook['data']['personEmail'].endswith('@webex.bot'):
    print("Message from another bot. Ignoring.")
```

### Environment Variable Protection

Sensitive configuration stored in environment variables:
- Bot tokens
- Database credentials
- Webhook secrets
- API keys

## 📊 Analytics & Metrics

The application includes comprehensive analytics:

**Usage Tracking:**
- Command usage statistics
- User interaction patterns
- Poll creation metrics
- Response analytics

**Performance Monitoring:**
- API response times
- Database query performance
- Error tracking
- Resource utilization

## 🚀 Deployment

### Local Development

1. **Set up environment variables**
2. **Install dependencies**: `pip3 install -r requirements.txt`
3. **Start MongoDB**
4. **Run application**: `python3 pollbot.py`
5. **Configure webhooks** pointing to your local server

### Production Deployment

**Docker Deployment:**
```bash
# Build image
docker build -f pollbot/Dockerfile -t pollbot-opensource .

# Run container
docker run -p 10060:10060 -i -t pollbot-opensource
```

**Environment Configuration:**
- Use environment variables for configuration
- Secure MongoDB connection
- HTTPS for webhook endpoints
- Load balancing for high availability

### Health Checks

The application provides health check endpoints:
- `/alive` - Basic health check
- `/ready` - Readiness check with database connectivity

## 🧪 Testing

### Manual Testing

1. **Add bot to Webex space**
2. **Test basic commands**: `@pollbot help`
3. **Create poll**: `@pollbot create poll`
4. **Test card interactions**
5. **Verify webhook delivery**

### Debug Mode

Enable debug mode for additional features:
```bash
python3 pollbot.py --debug
```

Debug mode provides:
- Additional test cards
- Detailed logging
- Development utilities

## 🔧 Customization

### Adding New Commands

1. **Add command logic** in `MainHandler.post()`
2. **Update help text** in `BaseHandler.help_msg()`
3. **Create card templates** if needed
4. **Test command functionality**

### Custom Card Templates

1. **Create JSON card file** in `pollbot/src/cards/`
2. **Add file path** to environment variables
3. **Update `CardBuilder`** to use new cards
4. **Test card rendering**

### Database Customization

1. **Modify schema** in `MongoController`
2. **Update queries** as needed
3. **Add indexes** for performance
4. **Test data operations**

## 🐛 Troubleshooting

### Common Issues

**Webhook Not Receiving Messages:**
- Verify webhook URLs are correct
- Check webhook secret configuration
- Ensure bot is added to space
- Verify firewall/network access

**Database Connection Issues:**
- Check MongoDB connection string
- Verify database credentials
- Test network connectivity
- Review database logs

**Card Rendering Problems:**
- Validate JSON card syntax
- Check file paths in environment variables
- Verify card schema compliance
- Test with simple cards first

### Debug Information

The application provides extensive logging:
- Webhook payloads
- API responses
- Database operations
- Error stack traces

## 📈 Performance Optimization

### Database Optimization

- **Indexes**: Create indexes on frequently queried fields
- **Connection Pooling**: Use MongoDB connection pooling
- **Query Optimization**: Optimize database queries
- **Data Cleanup**: Regular cleanup of expired polls

### Application Optimization

- **Async Operations**: Use Tornado's async features
- **Caching**: Cache frequently accessed data
- **Resource Management**: Proper cleanup of resources
- **Monitoring**: Track performance metrics

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Make changes** and test thoroughly
4. **Follow code style** and add documentation
5. **Submit pull request** with detailed description

### Development Guidelines

- **Code Style**: Follow PEP 8 Python style guidelines
- **Documentation**: Add docstrings and comments
- **Testing**: Test all new features thoroughly
- **Security**: Follow security best practices

## 📄 License

```
Copyright 2022 Cisco Systems Inc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## 🔗 Related Resources

- [Pollbot on Webex AppHub](https://apphub.webex.com/applications/pollbot-cisco-systems-12150-78220-99857)
- [Webex Bot Development Guide](https://developer.webex.com/docs/bots)
- [Webex Webhooks Documentation](https://developer.webex.com/docs/webhooks)
- [Adaptive Cards Documentation](https://developer.webex.com/docs/api/guides/cards)
- [Tornado Web Framework](https://www.tornadoweb.org/)

## 🆘 Support

- Create an issue in this repository
- Review [Webex Developer Documentation](https://developer.webex.com/docs)
- Contact [Webex Developer Support](https://developer.webex.com/support)

---

**Repository**: https://github.com/WebexSamples/Pollbot-OpenSource
