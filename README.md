# FragDropDetector

Automated monitoring system for r/MontagneParfums fragrance drops with real-time notifications and web configuration interface.

**Default: Fridays 12-5 PM ET** - Fully configurable via web interface.

## Features

### Core Monitoring
- **Automated Monitoring**: Scans r/MontagneParfums during configured drop windows
- **Stock Monitoring**: Tracks Montagne Parfums website for inventory changes
- **Unified Scheduling**: Both Reddit and stock monitoring use same drop window for simplicity
- **Smart Detection**: Pattern-based drop detection with confidence scoring
- **Real-time Alerts**: <2 minute notification latency during drop window

### Web Interface & Configuration
- **Modern Web UI**: Separated HTML/CSS/JavaScript with responsive design
- **Input Validation**: Pydantic-based validation for all API endpoints
- **Health Checks**: `/health`, `/health/ready`, `/health/live` endpoints for monitoring
- **Structured Logging**: Memory-conscious log rotation (10MB files, 3 backups)
- **Mobile-Optimized**: Works perfectly on phones and tablets

### Notifications & Data
- **Multiple Notifications**: Pushover (iOS), Discord webhooks, and Email support
- **Database Tracking**: SQLite database for historical drops and stock changes
- **API Endpoints**: RESTful API for all configuration and data access
- **Error Handling**: Comprehensive error handling with structured logging

### Deployment & Reliability
- **Memory Efficient**: Log rotation and optimized for resource-constrained devices
- **Raspberry Pi Ready**: Lightweight architecture perfect for Pi deployment
- **Production Ready**: Health checks, proper error handling, input validation

## Quick Start

### 1. Prerequisites

- Python 3.9+
- Reddit API credentials
- At least one notification service:
  - Pushover account ($4.99 iOS app) - Recommended for iPhone users
  - Discord server with webhook access
  - Email account with app-specific password

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/HurleySk/FragDropDetector.git
cd FragDropDetector

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 3. Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in:
   - Name: FragDropDetector
   - Type: Select "script"
   - Description: Fragrance drop monitor
   - Redirect URI: http://localhost:8080
4. Note your `client_id` (under "personal use script")
5. Note your `client_secret`

### 4. Notification Setup

#### Pushover (Recommended for iOS)
1. Sign up at https://pushover.net
2. Create an application in Pushover
3. Note your User Key and Application Token
4. Add to `.env`:
   ```
   PUSHOVER_USER_KEY=your_user_key
   PUSHOVER_APP_TOKEN=your_app_token
   ```

#### Discord Webhook
1. In your Discord server, go to Server Settings > Integrations
2. Create a new webhook
3. Copy the webhook URL
4. Add to `.env`:
   ```
   DISCORD_WEBHOOK_URL=your_webhook_url
   ```

#### Email
Configure in `.env` - see Email Notifications section below.

### 5. Configuration

Edit `.env` file:

```env
# Required
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret

# Notification Services (at least one required)
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_APP_TOKEN=your_app_token
DISCORD_WEBHOOK_URL=your_webhook_url

# Optional
SUBREDDIT=MontagneParfums
CHECK_INTERVAL=300
```

### 6. Run

```bash
# Test run (single check)
python main.py --once

# Continuous monitoring
python main.py

# Run web configuration interface
python web_server.py
```

Access web interface at: http://localhost:8080

**Note**: Default drop window is Fridays 12-5 PM ET. Configure via web interface or config.yaml.

## Web Configuration Interface

### Starting the Web Server

```bash
python web_server.py
```

Then access: http://localhost:8080

From other devices on network: http://[raspberry-pi-ip]:8080

### Web Interface Features

- **Modern Architecture**: Separated HTML/CSS/JavaScript with clean FastAPI backend
- **Input Validation**: All API endpoints use Pydantic validation for security
- **Health Monitoring**: Health check endpoints at `/health`, `/health/ready`, `/health/live`
- **Structured Logging**: Automatic log rotation (10MB files, 3 backups max)
- **Drop Window Configuration**: Set active days, times, and timezone
- **Stock Monitoring**: Configure website inventory tracking with notifications
- **Detection Settings**: Customize keywords and confidence thresholds
- **Notification Management**: Configure and test notification services
- **Live Statistics**: View drop count, recent detections, stock changes
- **Mobile Optimized**: Responsive design for phones and tablets
- **Error Handling**: Comprehensive error handling with user-friendly messages

### Finding Your Raspberry Pi IP

```bash
hostname -I
```

## Advanced Setup

### Systemd Service (Auto-start on boot)

```bash
# Copy service file
sudo cp fragdrop.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/fragdrop.service

# Enable and start
sudo systemctl enable fragdrop.service
sudo systemctl start fragdrop.service

# Check status
sudo systemctl status fragdrop.service
```

### Email Notifications

Add to `.env`:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=app_specific_password
EMAIL_RECIPIENTS=recipient@email.com
```

## Detection Keywords

The bot looks for:
- **Primary**: drop, release, available, launch, restock, "in stock"
- **Secondary**: limited, exclusive, sale, pre-order, batch, decant
- **Vendor patterns**: montagne parfums, official announcements
- **Exclusions**: "looking for", "where to buy", reviews

## Project Structure

```
FragDropDetector/
├── main.py                 # Main application runner
├── src/
│   ├── services/
│   │   ├── reddit_client.py    # Reddit API interface
│   │   ├── drop_detector.py    # Drop detection engine
│   │   └── notifiers.py        # Notification services
│   ├── models/
│   │   └── database.py         # Database models
│   └── utils/
├── config/
│   └── config.yaml         # Configuration file
├── data/                   # SQLite database
├── logs/                   # Log files
└── tests/                  # Test files
```

## Monitoring

Check logs:
```bash
tail -f logs/fragdrop.log
```

View database:
```bash
sqlite3 data/fragdrop.db
.tables
SELECT * FROM drops ORDER BY created_at DESC LIMIT 10;
```

## Troubleshooting

### Reddit API Error
- Verify client_id and client_secret
- Check Reddit app status
- Ensure user agent is set

### No Notifications
- Test webhook URL directly
- Check network connectivity
- Verify notification service credentials

### False Positives
- Adjust confidence_threshold in config.yaml
- Add exclusion patterns
- Report false positives for ML training

## Development

Run tests:
```bash
pytest tests/
```

Format code:
```bash
black src/ tests/
```

## Contributing

Pull requests welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Update documentation
5. Submit PR

## Future Enhancements

- [ ] Web dashboard
- [ ] Machine learning for detection
- [ ] Price tracking
- [ ] Multi-subreddit support
- [ ] Mobile app
- [ ] Browser extension

## License

MIT License - See LICENSE file

## Support

- Issues: https://github.com/HurleySk/FragDropDetector/issues
- Reddit: /u/YourUsername

## Credits

Built with:
- PRAW (Python Reddit API Wrapper)
- SQLAlchemy
- Discord Webhooks
- Love for fragrances