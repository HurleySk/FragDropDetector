# FragDropDetector

**Automated monitoring system for Montagne Parfums fragrance drops with real-time notifications and Parfumo ratings.**

Monitors r/MontagneParfums subreddit for drop announcements and tracks the Montagne Parfums website for stock changes, sending instant notifications when drops or restocks occur. Includes Parfumo ratings for original fragrances that Montagne clones.

## Features

### Dual Monitoring System
- **Reddit Scanner**: Monitors r/MontagneParfums for drop posts (default: Fridays 12-6 PM ET)
- **Stock Tracker**: 24/7 website monitoring for inventory changes (15-minute intervals)
- **Independent Schedules**: Reddit and stock monitoring run on separate, configurable schedules
- **Smart Detection**: ML-based pattern detection with 0.8 confidence threshold
- **Watchlist**: Priority notifications for specific fragrances you care about

### Web Interface
Modern single-page application with real-time updates:

- **Dashboard** - System health overview
  - Recent activity with last drop/restock within 7 days
  - Reddit monitor status with countdown to next window
  - Stock monitor status and schedule info
  - Watchlist alerts for out-of-stock items
  - Health checks for Reddit, database, notifications, monitoring

- **Activity Timeline** - Complete history
  - Filter by drops, stock changes, or all events
  - Date grouping (Today, Yesterday, day names, full dates)
  - Confidence badges and author attribution
  - Direct links to Reddit posts
  - Load more pagination (20 items per page)

- **Inventory Browser** - All 158+ products
  - Parfumo ratings and popularity scores for originals
  - Advanced sorting (Name, Price, Availability, Rating, Popularity)
  - Search and filtering
  - Bulk watchlist operations
  - Stock status indicators

- **Configuration Manager** - Full control
  - Reddit monitor settings and authentication status
  - Website monitor schedules and windows
  - Detection rules (keywords, trusted authors, threshold)
  - Notification services (Pushover, Discord, Email)
  - Parfumo integration via fragscrape API
  - System settings and log management

- **Responsive Design** - Dark mode support, mobile-friendly

### Notifications
- **Pushover**: iOS/Android push notifications (requires $5 app)
- **Discord**: Webhook integration (free)
- **Email**: SMTP support (Gmail, Outlook, etc.)
- **Configurable**: Enable per event type (drops, restocks, new products)

### Parfumo Integration
- **Automatic Rating Fetch**: Fetches Parfumo ratings via fragscrape API
- **Smart Mapping**: Maps Montagne products to original fragrances
- **Daily Updates**: Configurable scheduled rating updates (default: 2:00 AM)
- **Manual Triggers**: Update ratings on-demand via web interface
- **Popularity Scores**: Shows rating counts for each fragrance
- **Clickable Links**: Direct links to Parfumo pages from inventory
- **fragscrape Dependency**: Requires fragscrape API service (https://github.com/HurleySk/fragscrape)

### System Management
- **Automatic Log Rotation**: Size-based with configurable retention
- **Log Cleanup**: Automatic removal of old logs (30-day default)
- **Log Compression**: Gzip compression of rotated logs
- **Download Logs**: Export all logs as zip archive
- **Resource Monitoring**: Track disk usage and log statistics

## Prerequisites

Before installing FragDropDetector, ensure you have:

**System Requirements:**
- **Python 3.11+** - Modern Python with type hints
- **1GB+ RAM** - For browser automation and monitoring
- **Network Access** - To Reddit API and montagneparfums.com

**Required External Services:**
- **fragscrape API** - For Parfumo ratings integration
  - Repository: https://github.com/HurleySk/fragscrape
  - Must be running on http://localhost:3000 (or configure custom URL)
  - Install separately before using Parfumo features

**Optional but Recommended:**
- **Redis/Memcached** - For distributed caching (future)
- **Reverse Proxy** - nginx/Apache for production deployments

## Quick Start

### Automated Installation

```bash
git clone https://github.com/HurleySk/FragDropDetector.git
cd FragDropDetector
bash install.sh
```

The installer will:
1. Check system requirements (Python 3.11+, 1GB RAM)
2. Install Python dependencies
3. Set up Playwright for browser automation
4. Configure Reddit API credentials
5. Optionally set up systemd auto-start services
6. Guide you through Reddit authentication

### Manual Installation

See [Prerequisites](#prerequisites) section above for system requirements.

#### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/HurleySk/FragDropDetector.git
cd FragDropDetector

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 4. Configure environment
cp .env.example .env
# Edit .env with your Reddit API credentials
nano .env

# 5. Start the system
python main.py          # Terminal 1: Run monitor
python web_server.py   # Terminal 2: Start web interface

# Access web interface at http://localhost:8000
```

## Configuration

### Reddit API Setup (Required for Reddit Monitoring)

#### 1. Create Reddit App
1. Go to https://www.reddit.com/prefs/apps
2. Click "create app" or "create another app"
3. Select "script" type
4. Fill in details:
   - **name**: FragDropDetector (or your choice)
   - **redirect uri**: http://localhost:8080
5. Copy Client ID (under app name) and Secret

#### 2. Configure .env File
```bash
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_secret_here
REDDIT_USER_AGENT=FragDropDetector/1.0
REDDIT_USERNAME=your_reddit_username
```

#### 3. Authenticate (REQUIRED)

Reddit authentication is **required** because r/MontagneParfums has member-only posts invisible to anonymous users.

**For Headless Systems (Raspberry Pi, server):**
```bash
# On your local computer, create SSH tunnel:
ssh -L 8080:localhost:8080 pi@YOUR_PI_IP

# On the Pi/server, run authentication:
python generate_token_headless.py

# Follow browser instructions on your local machine
# Token is saved and persists indefinitely
```

**For Desktop Systems:**
```bash
python generate_token_headless.py
# Opens browser automatically for authentication
```

**Why This is Necessary:**
- r/MontagneParfums requires user authentication to view all posts
- Member-only posts are completely invisible without authentication
- Reddit intentionally blocks automated headless authentication for security
- SSH tunnel is the only reliable method for headless systems

### Drop Window Configuration

Default: Fridays 12:00 PM - 6:00 PM ET

Edit `config/config.yaml`:
```yaml
drop_window:
  enabled: true
  days_of_week: [4]      # 0=Monday, 4=Friday, 6=Sunday
  start_hour: 12         # 12 PM
  end_hour: 18           # 6 PM (18:00 in 24-hour format)
  timezone: America/New_York
```

For 24/7 monitoring, set `enabled: false`.

### Stock Monitoring Schedule (Independent)

Default: Every 15 minutes, 24/7

Edit `config/config.yaml`:
```yaml
stock_schedule:
  enabled: true
  check_interval: 900    # Seconds (900 = 15 minutes)
  window_enabled: false  # false = 24/7, true = use time windows
  timezone: America/New_York

  # Only used if window_enabled: true
  days_of_week: []       # Empty = all days
  start_hour: 9
  end_hour: 18
```

### Notification Services

#### Pushover (Recommended for Mobile)
Best for instant mobile notifications. Requires one-time $5 app purchase.

```bash
# Add to .env:
PUSHOVER_APP_TOKEN=your_app_token
PUSHOVER_USER_KEY=your_user_key
```

Get credentials at https://pushover.net

#### Discord
Free webhook integration.

```bash
# Add to .env:
DISCORD_WEBHOOK_URL=your_webhook_url
```

Create webhook: Server Settings → Integrations → Webhooks

#### Email
Any SMTP server (Gmail, Outlook, etc.)

```bash
# Add to .env:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
```

**Gmail Note**: Use App Passwords (Account Settings → Security → 2-Step Verification → App Passwords)

### Parfumo Configuration

**Note**: Parfumo integration requires the fragscrape API to be running. See [Prerequisites](#prerequisites) for installation instructions. If fragscrape is not available, the web interface will show a warning banner.

Edit `config/config.yaml`:
```yaml
parfumo:
  enabled: true
  fragscrape_url: "http://localhost:3000"  # fragscrape API endpoint
  auto_scrape_new: true    # Auto-fetch ratings for new products
  update_time: "02:00"     # Daily update time (24-hour format)
  rate_limit_delay: 2.0    # Seconds between requests
```

## Usage

### Web Interface

Access at http://localhost:8000 (or your server's IP)

**Navigation:**
- **Dashboard** (`/`) - System overview and quick actions
- **Activity** (`/#activity`) - Complete timeline of events
- **Inventory** (`/#inventory`) - Browse all products and manage watchlist
- **Configuration** (`/#configuration`) - Update all settings

**Watchlist Management:**
1. Browse to Inventory tab
2. Click star icon on products you want to track
3. Enable "Watchlist Only" toggle to filter view
4. Use checkboxes for bulk add/remove operations
5. Get notified when watchlisted items come back in stock

**Configuration Updates:**
1. Navigate to Configuration tab
2. Select appropriate section (Reddit, Website, Notifications, etc.)
3. Update settings in real-time
4. Changes apply immediately, no restart needed

### API Endpoints

The system exposes a REST API for programmatic access:

**System Status:**
- `GET /api/status` - Full system status
- `GET /api/status/monitor` - Monitor-specific status
- `GET /health` - Health check

**Drops:**
- `GET /api/drops?limit=10` - Recent drops
- `DELETE /api/drops/{id}` - Delete drop

**Stock:**
- `GET /api/stock/fragrances` - All fragrances (supports sorting, filtering)
- `GET /api/stock/changes?limit=10` - Recent stock changes
- `DELETE /api/stock/changes/{id}` - Delete stock change

**Watchlist:**
- `POST /api/stock/watchlist/add/{slug}` - Add to watchlist
- `POST /api/stock/watchlist/remove/{slug}` - Remove from watchlist
- `POST /api/watchlist/bulk` - Bulk add (body: `{"slugs": [...]}`)
- `DELETE /api/watchlist/bulk` - Bulk remove

**Configuration:**
- `GET /api/config` - Get all configuration
- `POST /api/config/reddit` - Update Reddit settings
- `POST /api/config/notifications` - Update notification settings
- `POST /api/config/detection` - Update detection rules

**Parfumo:**
- `GET /api/parfumo/status` - Get update status and fragscrape availability
- `POST /api/parfumo/update` - Trigger full rating update

**Logs:**
- `GET /api/logs/download` - Download all logs as zip
- `POST /api/logs/cleanup` - Manually trigger log cleanup

**Testing:**
- `POST /api/test/notifications` - Test all notification services

### Command Line

```bash
# Start main monitor
python main.py

# Start web interface
python web_server.py

# Run authentication
python generate_token_headless.py

# Check setup
python check_setup.py
```

## Production Deployment

**Important**: Ensure fragscrape API is installed and running before deploying FragDropDetector if you plan to use Parfumo integration. See [Prerequisites](#prerequisites).

### Systemd Services (Recommended)

For automatic startup on boot and proper process management:

```bash
# 1. Copy service files
sudo cp fragdrop.service /etc/systemd/system/
sudo cp fragdrop-web.service /etc/systemd/system/

# 2. Edit service files if needed (update paths, user)
sudo nano /etc/systemd/system/fragdrop.service
sudo nano /etc/systemd/system/fragdrop-web.service

# 3. Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable fragdrop fragdrop-web

# 4. Start services
sudo systemctl start fragdrop fragdrop-web

# 5. Check status
sudo systemctl status fragdrop
sudo systemctl status fragdrop-web

# 6. View logs
sudo journalctl -u fragdrop -f       # Monitor logs
sudo journalctl -u fragdrop-web -f   # Web interface logs
```

### Log Management

Automatic log rotation and cleanup:

```yaml
# config/config.yaml
logging:
  file_enabled: true
  file_path: logs/fragdrop.log
  max_file_size: 10              # MB per file
  backup_count: 5                # Number of rotated files to keep
  auto_cleanup:
    enabled: true
    max_age_days: 30             # Delete logs older than this
    max_total_size_mb: 100       # Maximum total log directory size
    cleanup_interval_hours: 24   # How often to run cleanup
    compress_old_logs: true      # Gzip rotated logs
```

Manage via web interface:
- **System & Logs tab** - View disk usage, download logs, trigger cleanup

### Reverse Proxy (Optional)

For exposing web interface on standard HTTP/HTTPS ports:

**Nginx:**
```nginx
server {
    listen 80;
    server_name fragdrop.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

**Apache:**
```apache
<VirtualHost *:80>
    ServerName fragdrop.yourdomain.com

    ProxyPass / http://localhost:8000/
    ProxyPassReverse / http://localhost:8000/
    ProxyPreserveHost On
</VirtualHost>
```

## Troubleshooting

### Common Issues

**"No module named playwright"**
```bash
pip install playwright
playwright install chromium
```

**Reddit 401 Error / Authentication Failed**
- Check `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in `.env`
- Re-run authentication: `python generate_token_headless.py`
- Check that your Reddit app type is "script" not "web app"

**Empty Inventory / No Products Found**
- Website structure may have changed
- Check logs: `tail -f logs/fragdrop.log`
- Verify network access: `curl https://www.montagneparfums.com`

**Port 8000 Already in Use**
```bash
# Find and kill process
lsof -i :8000
kill -9 <PID>

# Or use different port
python web_server.py --port 8001
```

**Parfumo Updates Failing**
- Check if fragscrape API is running: `curl http://localhost:3000/api/proxy/status`
- Web interface shows warning banner if fragscrape unavailable
- Verify fragscrape_url in `config/config.yaml` matches your fragscrape instance
- View logs for specific errors: `tail -f logs/fragdrop.log`
- Disable temporarily: set `parfumo.enabled: false` in config

**Watchlist Not Saving**
- Check write permissions on `config/config.yaml`
- Verify browser localStorage is enabled
- Check browser console for JavaScript errors

### Log Locations

- **Main logs**: `logs/fragdrop.log` (current)
- **Rotated logs**: `logs/fragdrop.log.1.gz`, `.2.gz`, etc.
- **Systemd logs**: `journalctl -u fragdrop -u fragdrop-web`
- **Database**: `data/fragdrop.db` (SQLite)
- **Parfumo status**: `data/parfumo_status.json`

### Debug Mode

Enable verbose logging in `config/config.yaml`:
```yaml
logging:
  level: DEBUG  # Change from INFO to DEBUG
```

Or via environment variable:
```bash
export LOG_LEVEL=DEBUG
python main.py
```

### Database Issues

**Reset Database (WARNING: Deletes all data):**
```bash
rm data/fragdrop.db
python main.py  # Will recreate with fresh schema
```

**Inspect Database:**
```bash
sqlite3 data/fragdrop.db
.tables  # List all tables
.schema posts  # View table schema
SELECT COUNT(*) FROM drops;  # Query drops
.quit
```

## Architecture

### Technology Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Frontend**: Vanilla JavaScript (SPA), CSS Grid, CSS Variables
- **Database**: SQLite with connection pooling
- **Scraping**: Playwright (headless Chromium)
- **Reddit API**: PRAW (Python Reddit API Wrapper)
- **Testing**: pytest (25+ tests)

### Project Structure
```
FragDropDetector/
├── main.py                       # Core monitoring loop (531 lines)
├── web_server.py                 # FastAPI application (180 lines)
├── generate_token_headless.py    # Reddit OAuth helper
├── install.sh                    # Automated installer
├── requirements.txt              # Python dependencies
│
├── src/                          # Core Python modules
│   ├── config/
│   │   ├── constants.py          # Centralized constants (13 classes)
│   │   └── settings.py           # Pydantic settings (type-safe)
│   ├── models/
│   │   ├── database.py           # SQLAlchemy ORM models
│   │   └── domain/
│   │       └── fragrance.py      # Unified Fragrance domain model
│   ├── services/
│   │   ├── container.py          # Dependency injection container
│   │   ├── schedule_manager.py   # Time window management
│   │   ├── reddit_client.py      # Reddit API wrapper
│   │   ├── drop_detector.py      # Pattern matching engine
│   │   ├── stock_monitor_enhanced.py  # Playwright scraper
│   │   ├── notifiers.py          # Notification handlers
│   │   ├── log_manager.py        # Log rotation and cleanup
│   │   ├── parfumo_scheduler.py  # Daily rating updates
│   │   ├── fragscrape_client.py  # fragscrape API client
│   │   ├── parfumo_updater.py    # Rating update orchestration
│   │   └── fragrance_mapper.py   # Product → original mapping
│   └── utils/
│       ├── logger.py             # Centralized logging
│       └── error_handler.py      # Error decorators and utilities
│
├── api/                          # Modular FastAPI routes
│   ├── routes/
│   │   ├── health.py             # Health checks
│   │   ├── status.py             # System status
│   │   ├── drops.py              # Drop endpoints
│   │   ├── stock.py              # Stock/inventory
│   │   ├── config.py             # Configuration
│   │   ├── logs.py               # Log management
│   │   ├── test.py               # Testing endpoints
│   │   └── parfumo.py            # Parfumo integration
│   ├── models.py                 # Pydantic validation models
│   └── dependencies.py           # Shared dependencies
│
├── static/                       # Frontend assets
│   ├── css/                      # Stylesheets
│   │   ├── design-system.css     # Core design tokens
│   │   ├── base.css              # Base styles
│   │   ├── theme.css             # Theme colors
│   │   └── *.css                 # Component styles
│   └── js/                       # JavaScript
│       ├── api/                  # API client layer
│       │   ├── client.js         # HTTP client with caching/retry
│       │   ├── endpoints.js      # Endpoint definitions
│       │   └── services.js       # Service functions
│       ├── config/               # Configuration modules (6 files)
│       │   ├── reddit-config.js
│       │   ├── notification-config.js
│       │   ├── detection-config.js
│       │   ├── stock-config.js
│       │   ├── logging-config.js
│       │   └── parfumo-config.js
│       ├── dashboard/            # Dashboard modules (5 files)
│       │   ├── utils.js          # Time formatting, navigation
│       │   ├── display.js        # Activity rendering
│       │   ├── health.js         # Health checks
│       │   ├── status.js         # Status cards
│       │   └── data.js           # Data loading
│       ├── state.js              # State management
│       ├── router.js             # SPA routing
│       ├── app.js                # Application controller
│       ├── dashboard-main.js     # Dashboard controller
│       ├── activity.js           # Activity timeline
│       ├── inventory.js          # Inventory browser
│       └── configuration.js      # Config manager
│
├── templates/
│   └── index.html                # SPA shell
│
├── tests/                        # Test suite
│   ├── conftest.py               # Fixtures and helpers
│   ├── test_fragrance_model.py   # Domain model tests (9 tests)
│   ├── test_schedule_manager.py  # Schedule logic (11 tests)
│   ├── test_database_integration.py  # DB tests (5 tests)
│   └── test_service_container.py # Container tests
│
├── config/
│   └── config.yaml               # User configuration
├── data/
│   ├── fragdrop.db               # SQLite database
│   └── parfumo_status.json       # Parfumo update status
├── logs/
│   └── fragdrop.log*             # Application logs
└── cache/                        # Temporary cache files
```

### Database Schema

**posts** - Reddit posts scanned
- `reddit_id`, `title`, `author`, `url`, `selftext`
- `link_flair_text`, `score`, `num_comments`
- `processed`, `created_utc`, `created_at`

**drops** - Detected drop events
- `post_reddit_id` (foreign key to posts)
- `confidence_score` (0.0-1.0)
- `detection_metadata` (JSON)
- `notified`, `notification_sent_at`

**fragrance_stock** - Product inventory (158+ fragrances)
- `slug` (unique identifier), `name`, `url`, `price`, `in_stock`
- `original_brand`, `original_name` (cloned from)
- `parfumo_id` (URL format), `parfumo_score`, `parfumo_votes`
- `rating_last_updated`, `first_seen`, `last_seen`

**stock_changes** - Stock change history
- `fragrance_slug`, `change_type` (restocked, out_of_stock, price_change, new_product)
- `old_value`, `new_value`, `notified`

**notifications** - Notification dispatch log
- `event_type`, `recipient`, `status`, `sent_at`

**settings** - Application settings cache

### Monitoring Logic

**Reddit Monitoring:**
1. Check if within drop window (e.g., Fridays 12-6 PM ET)
2. Scan new posts every 5 minutes (configurable)
3. Run pattern detection:
   - Primary keywords: "drop", "restock"
   - Secondary keywords: "limited", "available"
   - Vendor matching: "montagneparfums" variations
   - Trusted author bonus
   - Calculate confidence score (0.0-1.0)
4. If confidence ≥ 0.8, trigger notifications
5. Track processed posts to avoid duplicates

**Stock Monitoring:**
1. Check if within stock window (or 24/7)
2. Every N minutes (default: 15), scrape full catalog
3. Use Playwright to handle JavaScript-rendered content
4. Compare with previous scan:
   - Detect new products
   - Detect restocks (was out → now in stock)
   - Detect out of stock (was in → now out)
   - Detect price changes
5. Save changes to database
6. Send notifications (watchlist gets priority)
7. Cache results for 15 minutes to reduce load

## Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# By marker
pytest tests/ -m unit          # Unit tests only
pytest tests/ -m integration   # Integration tests only

# Specific file
pytest tests/test_fragrance_model.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Test Coverage
- Domain models (Fragrance)
- Schedule management (time windows)
- Database operations
- Service container
- 25+ passing tests

## Contributing

Contributions welcome! For major changes, please open an issue first to discuss what you would like to change.

### Development Setup
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Run test suite (`pytest tests/ -v`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

## License

This project is open source. Please check the repository for license details.

## Support

- **Issues**: https://github.com/HurleySk/FragDropDetector/issues
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Reddit**: r/MontagneParfums community

## Credits

Built for the r/MontagneParfums community to never miss a fragrance drop.
