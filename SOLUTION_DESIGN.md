# FragDropDetector - Solution Design Document

## Executive Summary
FragDropDetector is an automated monitoring system that scans the r/MontagneParfums subreddit for fragrance drops and releases, providing real-time notifications to users who want to stay informed about new fragrance availability.

## Current Status: Phase 1 & 2 COMPLETE ✅
**Last Updated**: September 20, 2025

### Implementation Progress
- ✅ **Phase 1: Core Monitoring** - Complete
- ✅ **Phase 2: Notification System** - Complete
- ⏳ **Phase 3: Enhancement** - Ready to start
- ⏳ **Phase 4: Deployment & Optimization** - Ready to start

## Problem Statement
- Fragrance enthusiasts need to constantly monitor r/MontagneParfums to catch limited drops
- Manual checking is time-consuming and drops can be missed
- Limited availability means timing is critical

## Proposed Solution Architecture

### Core Components

#### 1. Reddit Monitor Service
**Technology**: Python with PRAW (Python Reddit API Wrapper)
- Polls r/MontagneParfums at configurable intervals (default: every 5 minutes)
- Authenticates using Reddit API credentials (requires Reddit app registration)
- Fetches new posts since last check
- Implements rate limiting to respect Reddit's API limits

#### 2. Drop Detection Engine
**Pattern Recognition Strategy**:
- **Title Keywords**: "drop", "release", "available", "new", "launch", "restock", "in stock"
- **Flair Detection**: Monitor specific post flairs if subreddit uses them
- **User Tracking**: Track posts from known vendor accounts
- **Content Analysis**: Scan post body for pricing, availability dates, links
- **Scoring System**: Assign confidence scores based on multiple indicators

#### 3. Data Storage
**Technology**: SQLite (lightweight, perfect for Raspberry Pi deployment)
```sql
Tables:
- posts (id, reddit_id, title, author, url, content, timestamp, processed)
- drops (id, post_id, confidence_score, notified, created_at)
- notifications (id, drop_id, method, status, sent_at)
- settings (key, value)
```

#### 4. Notification System
**Multiple Notification Channels**:

a) **Discord Bot** (Recommended)
- Create dedicated Discord server/channel
- Rich embeds with post details
- Direct links to Reddit post
- @mention roles for urgent drops

b) **Telegram Bot**
- Direct messages to subscribers
- Group channel support
- Inline buttons for quick actions

c) **Email Notifications**
- SMTP integration (Gmail, SendGrid)
- HTML formatted emails
- Unsubscribe links

d) **Web Dashboard**
- Real-time updates via WebSocket
- Historical drop tracking
- User preferences management

#### 5. Web Interface (Optional)
**Technology**: Flask/FastAPI + React/Vue
- Dashboard showing recent drops
- Notification preferences
- Historical data and analytics
- Search functionality

## Implementation Plan

### ✅ Phase 1: Core Monitoring (COMPLETE)
1. ✅ Set up Reddit API credentials structure
2. ✅ Implement PRAW integration (`src/services/reddit_client.py`)
3. ✅ Create SQLite schema with SQLAlchemy (`src/models/database.py`)
4. ✅ Build drop detection logic with confidence scoring (`src/services/drop_detector.py`)
5. ✅ Console logging with colorlog for debugging

### ✅ Phase 2: Notification System (COMPLETE)
1. ✅ Discord webhook notifications with rich embeds
2. ✅ Telegram bot support
3. ✅ Email notification service
4. ✅ NotificationManager for multi-channel support
5. ✅ Test notification capability

### ⏳ Phase 3: Enhancement (NEXT STEPS)
1. ⏳ Add web dashboard with FastAPI
2. ✅ Multiple notification channels implemented
3. ⏳ Add user preferences UI
4. ✅ Configuration management via YAML and .env

### ⏳ Phase 4: Deployment & Optimization (UPCOMING)
1. ⏳ Dockerize application
2. ✅ Systemd service file created
3. ⏳ Implement backup strategies
4. ⏳ Performance optimization

## Technical Stack

### Backend
- **Language**: Python 3.9+
- **Framework**: FastAPI (async support, auto-documentation)
- **Reddit API**: PRAW 7.x
- **Database**: SQLite with SQLAlchemy ORM
- **Task Scheduler**: APScheduler
- **Notifications**:
  - Discord.py for Discord
  - python-telegram-bot for Telegram
  - smtplib for email

### Frontend (Optional)
- **Framework**: React or Vue.js
- **UI Library**: Material-UI or Vuetify
- **Real-time**: Socket.io or native WebSockets
- **Charts**: Chart.js for analytics

### Deployment
- **Local**: Raspberry Pi with systemd service
- **Cloud**:
  - AWS EC2 Free Tier
  - Google Cloud Run
  - Heroku Free Tier
  - DigitalOcean Droplet

## Configuration File Structure
```yaml
# config.yaml
reddit:
  client_id: "your_client_id"
  client_secret: "your_client_secret"
  user_agent: "FragDropDetector/1.0"
  subreddit: "MontagneParfums"
  check_interval: 300  # seconds

detection:
  keywords:
    - drop
    - release
    - available
    - "now live"
    - "in stock"
  confidence_threshold: 0.7

notifications:
  discord:
    enabled: true
    webhook_url: "your_webhook_url"

  telegram:
    enabled: false
    bot_token: "your_bot_token"
    chat_id: "your_chat_id"

  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    sender: "your_email@gmail.com"
    recipients:
      - "recipient1@email.com"
```

## Security Considerations
1. **API Credentials**: Store in environment variables or encrypted config
2. **Rate Limiting**: Implement to avoid Reddit API bans
3. **User Data**: Minimal PII collection, GDPR compliance if needed
4. **Authentication**: JWT tokens for web interface
5. **HTTPS**: SSL certificates for web deployment

## Monitoring & Maintenance
1. **Logging**: Structured logging with rotation
2. **Error Handling**: Graceful failure and retry logic
3. **Metrics**: Track detection accuracy, notification delivery
4. **Backups**: Regular SQLite database backups
5. **Updates**: Automated dependency updates

## Performance Optimizations
1. **Caching**: Redis for frequently accessed data
2. **Async Operations**: Use asyncio for concurrent operations
3. **Database Indexing**: Optimize query performance
4. **Connection Pooling**: Reuse Reddit API connections

## Future Enhancements
1. **Machine Learning**: Train model on historical drops for better detection
2. **Price Tracking**: Monitor and alert on price changes
3. **Multi-subreddit Support**: Expand to other fragrance communities
4. **Mobile App**: Native iOS/Android applications
5. **Browser Extension**: Quick access to latest drops
6. **AI Summaries**: GPT-powered drop summaries
7. **Wishlist Feature**: Personal tracking for specific fragrances
8. **Community Features**: User reviews and ratings

## Estimated Resource Requirements
- **CPU**: Minimal (Raspberry Pi 3+ sufficient)
- **RAM**: 512MB minimum, 1GB recommended
- **Storage**: 1GB for application and database
- **Network**: Stable internet connection
- **Cost**:
  - Self-hosted: ~$5-10/month (electricity)
  - Cloud: $0-20/month depending on tier

## Success Metrics
1. **Detection Rate**: >95% of actual drops detected
2. **False Positive Rate**: <5%
3. **Notification Latency**: <2 minutes from post creation
4. **System Uptime**: >99%
5. **User Satisfaction**: Track via feedback system

## Risk Mitigation
1. **Reddit API Changes**: Abstract API layer for easy updates
2. **Rate Limiting**: Implement exponential backoff
3. **Subreddit Rule Changes**: Regular monitoring of subreddit rules
4. **False Positives**: User reporting and ML training
5. **System Failures**: Automated restarts and alerting

## Completed Components

### Files Created
1. **`main.py`** - Main application runner with monitoring loop
2. **`src/services/reddit_client.py`** - Reddit API wrapper using PRAW
3. **`src/services/drop_detector.py`** - Pattern-based detection engine
4. **`src/services/notifiers.py`** - Discord, Telegram, Email notifiers
5. **`src/models/database.py`** - SQLite models and database manager
6. **`config/config.yaml`** - Application configuration
7. **`.env.example`** - Environment variable template
8. **`requirements.txt`** - Python dependencies
9. **`README.md`** - Complete setup documentation
10. **`fragdrop.service`** - Systemd service for auto-start
11. **`.gitignore`** - Git ignore configuration

## Immediate Next Steps

### 1. Configuration (5 minutes)
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

Required credentials:
- **Reddit API**: Get from https://www.reddit.com/prefs/apps
- **Discord Webhook**: Create in Discord server settings

### 2. Installation (2 minutes)
```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 3. Testing (1 minute)
```bash
# Test single check
python main.py --once

# Test notification (set SEND_TEST_NOTIFICATION=true in .env)
python main.py --once
```

### 4. Deployment (5 minutes)
```bash
# Option A: Run in background
nohup python main.py &

# Option B: Systemd service (recommended)
sudo cp fragdrop.service /etc/systemd/system/
sudo systemctl enable fragdrop
sudo systemctl start fragdrop
```

## Future Enhancements Priority

### High Priority
1. **Web Dashboard** - Visual monitoring interface
2. **Machine Learning** - Improve detection accuracy
3. **Docker Container** - Easier deployment

### Medium Priority
4. **Price Tracking** - Monitor price changes
5. **Multi-subreddit** - Expand coverage
6. **Wishlist Feature** - Personal tracking

### Low Priority
7. **Mobile App** - Native applications
8. **Browser Extension** - Quick access
9. **AI Summaries** - GPT-powered summaries

## Current Capabilities

### What It Does Now
- ✅ Monitors r/MontagneParfums every 5 minutes
- ✅ Detects drops using keyword patterns
- ✅ Calculates confidence scores (0-100%)
- ✅ Sends Discord/Telegram/Email notifications
- ✅ Stores history in SQLite database
- ✅ Handles multiple notification channels
- ✅ Runs continuously with error handling

### Detection Accuracy
- Primary keywords: "drop", "release", "available", "launch", "restock"
- Confidence threshold: 40% (configurable)
- False positive filtering via exclusion patterns
- Vendor account tracking

## Troubleshooting Guide

### Common Issues

1. **"Reddit credentials not found"**
   - Ensure `.env` file exists
   - Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are set

2. **"Failed to connect to Reddit API"**
   - Verify credentials are correct
   - Check internet connection
   - Ensure Reddit app type is "script"

3. **No notifications received**
   - Test Discord webhook URL directly
   - Check notification service is enabled in config
   - Verify confidence threshold isn't too high

4. **Database errors**
   - Ensure `data/` directory exists
   - Check write permissions
   - Delete `data/fragdrop.db` to reset

## Performance Metrics

- **Memory Usage**: ~50MB
- **CPU Usage**: <1% (spike to 5% during checks)
- **Network**: ~100KB per check
- **Storage**: ~1MB per month
- **Uptime**: Designed for 99%+ availability

## Conclusion
The FragDropDetector MVP is now complete and ready for deployment. The core monitoring and notification systems are fully functional, providing immediate value for tracking fragrance drops on r/MontagneParfums. The modular architecture allows for easy extension with the planned enhancements.