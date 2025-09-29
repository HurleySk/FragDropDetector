# FragDropDetector

Automated monitoring system for Montagne Parfums fragrance drops and stock changes with real-time notifications.

**What it does:** Monitors r/MontagneParfums subreddit for drop announcements and tracks the Montagne Parfums website for stock changes, sending instant notifications via Pushover, Discord, or Email when drops or restocks occur.

## Features

### Core Monitoring
- **Reddit Scanner**: Monitors r/MontagneParfums for drops (Fridays 12-6 PM ET default)
- **Stock Tracker**: Independent 24/7 website monitoring (15-minute intervals)
- **Smart Detection**: Pattern-based detection with 0.8 confidence threshold
- **Watchlist**: Priority notifications for specific fragrances

### Web Interface
- **Dashboard**: System health, recent activity, watchlist widget
- **Inventory**: Browse all 158+ products with search, filters, and bulk operations
- **Configuration**: Full control over all settings:
  - Detection Rules: Keywords, trusted authors, confidence threshold
  - Monitoring schedules and time windows
  - Notification services setup
  - System & Logs management
- Enhanced toast notifications for instant feedback
- Clean, responsive design with dark mode support

### Notifications
- **Pushover**: iOS/Android push notifications
- **Discord**: Webhook integration
- **Email**: SMTP support
- Configurable for different event types (drops, restocks, new products)

### System Management
- **Automatic Log Rotation**: Size-based rotation with configurable retention
- **Log Cleanup**: Automatic removal of old logs to prevent disk filling
- **Log Compression**: Automatic gzip compression of rotated logs
- **Web-Based Control**: Manage all logging settings through the interface

## Quick Start

### Easy Installation (Recommended)

#### Option 1: One-Line Install
```bash
curl -sSL https://raw.githubusercontent.com/HurleySk/FragDropDetector/main/install.sh | bash
```

#### Option 2: Clone and Install
```bash
# Clone the repository
git clone https://github.com/HurleySk/FragDropDetector.git
cd FragDropDetector

# Run the installer
bash install.sh
```

The installer will:
- Check system requirements
- Install dependencies
- Set up Python environment
- Configure Reddit API credentials
- Set up auto-start services (optional)
- Guide you through authentication

### Manual Installation

#### Prerequisites
```bash
# System requirements
- Python 3.11+
- 1GB+ RAM
- Network access to Reddit and montagneparfums.com
```

#### Steps
```bash
# 1. Setup Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

```bash
# 2. Configure environment
cp .env.example .env
# Edit .env with your Reddit API credentials (required)
# Add notification service credentials (optional)

# 3. Start the system
python main.py          # Run the monitor
python web_server.py   # Start web interface (in another terminal)
# Access at http://localhost:8000
```

## Production Deployment

### Systemd Services (Recommended)
For automatic startup on boot:

```bash
# Copy service files
sudo cp fragdrop.service /etc/systemd/system/
sudo cp fragdrop-web.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable fragdrop fragdrop-web
sudo systemctl start fragdrop fragdrop-web

# Check status
sudo systemctl status fragdrop fragdrop-web

# View logs
journalctl -u fragdrop -f      # Monitor logs
journalctl -u fragdrop-web -f  # Web interface logs
```

## Configuration

### Reddit Setup (Required for Reddit Monitoring)

#### 1. Create Reddit App
1. Go to https://www.reddit.com/prefs/apps
2. Create app (script type)
3. Add Client ID and Secret to `.env`

#### 2. User Authentication (REQUIRED)
Without authentication, Reddit monitoring is **completely disabled**.

**SSH Tunnel Method** (For Headless Systems):
```bash
# 1. SSH with port forwarding from your local machine:
ssh -L 8080:localhost:8080 pi@YOUR_PI_IP

# 2. Run authentication script on Pi:
python generate_token_headless.py

# 3. Follow browser instructions on your local machine
# Token is automatically saved and persists indefinitely
```

**Why Authentication is Required:**
- r/MontagneParfums has member-only posts invisible to anonymous users
- Notification links won't work without proper authentication
- Stock monitoring continues to work independently

**Note**: Reddit intentionally blocks automated headless authentication for security. SSH tunnel is the only reliable method for headless systems.

### Drop Windows
Default: Fridays 12-6 PM ET
```yaml
# config/config.yaml
drop_window:
  days_of_week: [4]  # 0=Mon, 4=Fri
  start_hour: 12
  end_hour: 18        # 6 PM (18:00)
  timezone: America/New_York
```

### Stock Schedule (Independent)
Default: Every 15 minutes, 24/7
```yaml
# config/config.yaml
stock_schedule:
  enabled: true
  check_interval: 900   # 15 minutes
  window_enabled: false # Monitor 24/7
  timezone: America/New_York
  days_of_week: []      # Empty = all days
```

### Logging Management
Configurable through web interface or `config.yaml`:
```yaml
logging:
  file_enabled: true
  file_path: logs/fragdrop.log
  max_file_size: 10  # MB per file
  backup_count: 5    # Rotated files to keep
  auto_cleanup:
    enabled: true
    max_age_days: 30         # Delete logs older than this
    max_total_size_mb: 100   # Maximum total log size
    cleanup_interval_hours: 24
    compress_old_logs: true  # Gzip rotated logs
```

Access through **System & Logs** tab in web interface to:
- View disk usage and log statistics
- Download all logs as zip archive
- Manually trigger cleanup
- Configure all settings

### Notifications
- **Pushover**: Best for mobile, requires $5 app
- **Discord**: Free, create webhook in server settings
- **Email**: Any SMTP server (Gmail, Outlook, etc.)

## Usage

### Web Interface
- **Dashboard** (`/`): System overview and quick actions
- **Inventory** (`/#inventory`): Browse products, manage watchlist
- **Configuration** (`/#configuration`): Update all settings
  - Reddit Monitor, Website Monitor, Detection Rules
  - Notifications (Pushover, Discord, Email)
  - System & Logs management

### Watchlist
1. Click star icon on any product to watch
2. Get notified when items come back in stock
3. Use "Watchlist Only" toggle to filter view
4. Bulk operations with checkboxes

### API Endpoints
```
GET  /api/status                     # System status
GET  /api/stock/fragrances           # All products with filters
POST /api/stock/watchlist/add/{slug} # Add to watchlist
POST /api/watchlist/bulk             # Bulk operations
POST /api/test/notifications         # Test notifications
POST /api/config/logging             # Update logging configuration
GET  /api/logs/usage                 # Get log statistics
POST /api/logs/cleanup               # Trigger manual cleanup
GET  /api/logs/download              # Download logs as zip
```

## Architecture

```
FragDropDetector/
├── main.py                 # Core monitoring loop
├── web_server.py          # FastAPI web interface
├── generate_token_headless.py # Reddit OAuth setup
├── src/
│   ├── services/          # Business logic
│   │   ├── reddit_client.py         # Reddit API wrapper
│   │   ├── drop_detector.py         # Pattern matching
│   │   ├── stock_monitor_enhanced.py # Playwright scraper
│   │   ├── notifiers.py             # Notification handlers
│   │   └── log_manager.py           # Log rotation and cleanup
│   └── models/
│       └── database.py    # SQLAlchemy models
├── static/                # Frontend assets (JS/CSS)
├── templates/             # HTML templates
├── config/
│   └── config.yaml        # User configuration
├── data/                  # SQLite database
├── logs/                  # Application logs
└── cache/                 # Temporary cache files
```

### Database Schema
- `posts`: Reddit posts cache
- `drops`: Detected drops with confidence scores
- `fragrance_stock`: Product inventory (158+ items)
- `stock_changes`: Historical changes
- `notifications`: Sent notification log

### Key Technologies
- **Backend**: Python, FastAPI, SQLAlchemy, Playwright
- **Frontend**: Vanilla JS, CSS Grid, CSS Variables
- **Database**: SQLite
- **Scraping**: Playwright (handles JavaScript-rendered content)

## Monitoring Logic

### Reddit Monitoring
1. **Drop Window Check**: Only monitors during configured hours (Fridays 12-6 PM ET by default)
2. **Reddit Scan**: Checks new posts every 5 minutes (configurable)
3. **Pattern Detection**:
   - Primary keywords: drop, restock
   - Secondary keywords: limited
   - Vendor matching: montagneparfums variations
   - Confidence scoring (threshold: 0.8)

### How Drop Detection Works
The system tracks the last check timestamp and only processes **new posts** since that time. Each post gets a confidence score:

**High-Impact Signals** (0.3-0.6 points each):
- Trusted authors (configurable via web interface)
- "Restock" in title or flair
- Time patterns ("5pm EST", "today at")
- Vendor mentions ("Montagne Parfums", "MP")

**Medium-Impact** (0.1-0.2 points):
- Keywords: drop, release, available, launch
- Purchase links in post

**Auto-Excluded**: Posts with "looking for", "wtb/wts", "iso", "recommendation", "review"

Posts scoring ≥0.8 trigger notifications. The system remembers processed posts to avoid duplicates.

### Stock Monitoring (Independent)
1. **Flexible Scheduling**: Runs on separate schedule (15 minutes by default)
2. **Optional Time Windows**: Can restrict to specific days/hours or monitor 24/7
3. **Full Inventory Scan**: Scrapes entire product catalog using Playwright
4. **Change Detection**: Compares with previous scan for new/restocked/price changes
5. **Smart Caching**: 15-minute cache to reduce server load

## Troubleshooting

### Common Issues
- **"No module named playwright"**: Run `playwright install chromium`
- **Reddit 401 Error**: Check Client ID/Secret in `.env`
- **Empty inventory**: Website may have changed structure
- **Port 8000 in use**: Kill existing process or change port

### Logs
- Main logs: `logs/fragdrop.log` (rotated automatically)
- Archive logs: `logs/fragdrop.log.1.gz`, `.2.gz`, etc.
- Systemd logs: `journalctl -u fragdrop -u fragdrop-web`
- Database: `data/fragdrop.db` (SQLite)

## Development

### Adding Features
- Notification services: Extend `NotificationManager` in `notifiers.py`
- New scrapers: Add to `services/` with async pattern
- API endpoints: Add to `web_server.py` with FastAPI decorators

### Testing
```bash
# Test notifications
curl -X POST http://localhost:8000/api/test/notifications

# Check stock
curl http://localhost:8000/api/stock/fragrances

# Add to watchlist
curl -X POST http://localhost:8000/api/stock/watchlist/add/product-slug
```

## Contributing

Pull requests welcome. For major changes, open an issue first.
