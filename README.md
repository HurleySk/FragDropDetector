# FragDropDetector

Automated monitoring system for r/MontagneParfums fragrance drops with real-time notifications.

## Features

- 🔍 **Automated Monitoring**: Scans r/MontagneParfums every 5 minutes for new drops
- 🎯 **Smart Detection**: Pattern-based drop detection with confidence scoring
- 📱 **Multiple Notifications**: Discord, Telegram, and Email support
- 💾 **Database Tracking**: SQLite database for historical data
- 🚀 **Lightweight**: Perfect for Raspberry Pi deployment
- ⚡ **Real-time Alerts**: <2 minute notification latency

## Quick Start

### 1. Prerequisites

- Python 3.9+
- Reddit API credentials
- Discord webhook URL (recommended)

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

### 4. Discord Webhook Setup

1. Open Discord server settings
2. Go to Integrations > Webhooks
3. Click "New Webhook"
4. Name it "FragDropDetector"
5. Copy the webhook URL

### 5. Configuration

Edit `.env` file:

```env
# Required
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
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

### Telegram Notifications

1. Create bot with @BotFather
2. Get bot token
3. Get your chat ID
4. Add to `.env`:
```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
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
- Love for fragrances 💝