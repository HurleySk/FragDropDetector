const API_BASE = '';

function showAlert(message, type = 'info') {
    const alert = document.getElementById('alert');
    alert.className = `alert ${type}`;
    alert.textContent = message;
    alert.style.display = 'block';

    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();

        document.getElementById('status-drops').textContent = data.drops_detected;
        document.getElementById('status-posts').textContent = data.posts_processed;
        document.getElementById('status-fragrances').textContent = data.fragrances_tracked;
        document.getElementById('status-stock-changes').textContent = data.recent_stock_changes;

        if (data.next_window) {
            const nextDate = new Date(data.next_window);
            const now = new Date();
            const hours = Math.floor((nextDate - now) / (1000 * 60 * 60));
            document.getElementById('status-next').textContent = `${hours}h`;
        }

        const badges = [];
        if (data.notifications_enabled.pushover) badges.push('<span class="badge active">Pushover</span>');
        if (data.notifications_enabled.discord) badges.push('<span class="badge active">Discord</span>');
        if (badges.length === 0) badges.push('<span class="badge inactive">None</span>');
        document.getElementById('notification-badges').innerHTML = badges.join('');
    } catch (error) {
        console.error('Failed to load status:', error);
    }
}

async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        const data = await response.json();

        // Load Reddit settings
        document.getElementById('reddit-client-id').value = data.reddit.client_id || '';
        document.getElementById('reddit-client-secret').value = data.reddit.client_secret || '';
        document.getElementById('reddit-subreddit').value = data.reddit.subreddit || 'MontagneParfums';
        document.getElementById('reddit-interval').value = data.reddit.check_interval || 300;

        // Load notification settings
        document.getElementById('pushover-app-token').value = data.notifications.pushover_app_token || '';
        document.getElementById('pushover-user-key').value = data.notifications.pushover_user_key || '';
        document.getElementById('discord-webhook').value = data.notifications.discord_webhook_url || '';

        // Load detection settings
        if (data.detection.primary_keywords) {
            document.getElementById('primary-keywords').value = data.detection.primary_keywords.join('\n');
        }
        if (data.detection.secondary_keywords) {
            document.getElementById('secondary-keywords').value = data.detection.secondary_keywords.join('\n');
        }
        if (data.detection.confidence_threshold) {
            document.getElementById('confidence-threshold').value = data.detection.confidence_threshold;
        }

        // Load drop window settings
        if (data.drop_window) {
            document.getElementById('window-enabled').value = data.drop_window.enabled !== false ? 'true' : 'false';
            if (data.drop_window.timezone) {
                document.getElementById('window-timezone').value = data.drop_window.timezone;
            }

            // Clear all day checkboxes first
            for (let i = 0; i < 7; i++) {
                const checkbox = document.getElementById(`day-${i}`);
                if (checkbox) {
                    checkbox.checked = false;
                }
            }

            // Check the configured days
            if (data.drop_window.days_of_week) {
                data.drop_window.days_of_week.forEach(day => {
                    const checkbox = document.getElementById(`day-${day}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }

            // Set times
            if (data.drop_window.start_hour !== undefined && data.drop_window.start_minute !== undefined) {
                const startTime = `${String(data.drop_window.start_hour).padStart(2, '0')}:${String(data.drop_window.start_minute).padStart(2, '0')}`;
                document.getElementById('window-start-time').value = startTime;
            }
            if (data.drop_window.end_hour !== undefined && data.drop_window.end_minute !== undefined) {
                const endTime = `${String(data.drop_window.end_hour).padStart(2, '0')}:${String(data.drop_window.end_minute).padStart(2, '0')}`;
                document.getElementById('window-end-time').value = endTime;
            }
        }

        // Load stock monitoring settings
        if (data.stock_monitoring) {
            document.getElementById('stock-enabled').checked = data.stock_monitoring.enabled || false;

            if (data.stock_monitoring.notifications) {
                document.getElementById('notify-new-products').checked = data.stock_monitoring.notifications.new_products || false;
                document.getElementById('notify-restocked').checked = data.stock_monitoring.notifications.restocked_products || false;
                document.getElementById('notify-price-changes').checked = data.stock_monitoring.notifications.price_changes || false;
                document.getElementById('notify-out-of-stock').checked = data.stock_monitoring.notifications.out_of_stock || false;
            }
        }
    } catch (error) {
        console.error('Failed to load config:', error);
        showAlert('Failed to load configuration', 'error');
    }
}

async function loadDrops() {
    try {
        const response = await fetch(`${API_BASE}/api/drops?limit=10`);
        const drops = await response.json();

        const dropsList = document.getElementById('drops-list');
        if (drops.length === 0) {
            dropsList.innerHTML = '<p style="color: #718096;">No drops detected yet</p>';
        } else {
            dropsList.innerHTML = drops.map(drop => `
                <div class="drop-item">
                    <div class="drop-title">${drop.title}</div>
                    <div class="drop-meta">
                        ${new Date(drop.created_at).toLocaleString()} •
                        Confidence: ${(drop.confidence * 100).toFixed(0)}%
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to load drops:', error);
    }
}

async function loadStockChanges() {
    try {
        const response = await fetch(`${API_BASE}/api/stock/changes?limit=10`);
        const changes = await response.json();

        const changesList = document.getElementById('stock-changes-list');
        if (changes.length === 0) {
            changesList.innerHTML = '<p style="color: #718096;">No stock changes detected yet</p>';
        } else {
            changesList.innerHTML = changes.map(change => `
                <div class="drop-item">
                    <div class="drop-title">${change.fragrance_name}</div>
                    <div class="drop-meta">
                        Type: ${change.change_type} |
                        ${change.old_value ? 'From: ' + change.old_value + ' | ' : ''}
                        ${change.new_value ? 'To: ' + change.new_value + ' | ' : ''}
                        ${new Date(change.detected_at).toLocaleString()}
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to load stock changes:', error);
    }
}

async function testRedditConnection() {
    showAlert('Testing Reddit connection...', 'info');

    const config = {
        client_id: document.getElementById('reddit-client-id').value,
        client_secret: document.getElementById('reddit-client-secret').value,
        user_agent: 'FragDropDetector/1.0',
        subreddit: document.getElementById('reddit-subreddit').value,
        check_interval: parseInt(document.getElementById('reddit-interval').value),
        post_limit: 50
    };

    try {
        const response = await fetch(`${API_BASE}/api/test/reddit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        showAlert(result.message, result.success ? 'success' : 'error');
    } catch (error) {
        showAlert('Failed to test connection', 'error');
    }
}

async function testNotifications() {
    showAlert('Sending test notifications...', 'info');

    try {
        const response = await fetch(`${API_BASE}/api/test/notifications`, {
            method: 'POST'
        });

        const results = await response.json();
        let messages = [];

        for (const [service, result] of Object.entries(results)) {
            if (result.success) {
                messages.push(`${service}: Success`);
            } else {
                messages.push(`${service}: ${result.message}`);
            }
        }

        showAlert(messages.join(', '), 'info');
    } catch (error) {
        showAlert('Failed to test notifications', 'error');
    }
}

// Form submissions
document.getElementById('reddit-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const config = {
        client_id: document.getElementById('reddit-client-id').value,
        client_secret: document.getElementById('reddit-client-secret').value,
        user_agent: 'FragDropDetector/1.0',
        subreddit: document.getElementById('reddit-subreddit').value,
        check_interval: parseInt(document.getElementById('reddit-interval').value),
        post_limit: 50
    };

    try {
        const response = await fetch(`${API_BASE}/api/config/reddit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showAlert('Reddit configuration saved successfully', 'success');
        } else {
            showAlert('Failed to save Reddit configuration', 'error');
        }
    } catch (error) {
        showAlert('Failed to save configuration', 'error');
    }
});

document.getElementById('notification-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const config = {
        pushover_app_token: document.getElementById('pushover-app-token').value,
        pushover_user_key: document.getElementById('pushover-user-key').value,
        discord_webhook_url: document.getElementById('discord-webhook').value
    };

    try {
        const response = await fetch(`${API_BASE}/api/config/notifications`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showAlert('Notification configuration saved successfully', 'success');
        } else {
            showAlert('Failed to save notification configuration', 'error');
        }
    } catch (error) {
        showAlert('Failed to save configuration', 'error');
    }
});

document.getElementById('detection-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const config = {
        primary_keywords: document.getElementById('primary-keywords').value.split('\n').filter(k => k.trim()),
        secondary_keywords: document.getElementById('secondary-keywords').value.split('\n').filter(k => k.trim()),
        confidence_threshold: parseFloat(document.getElementById('confidence-threshold').value),
        known_vendors: ['montagneparfums', 'montagne_parfums']
    };

    try {
        const response = await fetch(`${API_BASE}/api/config/detection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showAlert('Detection configuration saved successfully', 'success');
        } else {
            showAlert('Failed to save detection configuration', 'error');
        }
    } catch (error) {
        showAlert('Failed to save configuration', 'error');
    }
});

document.getElementById('window-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get selected days
    const days = [];
    for (let i = 0; i < 7; i++) {
        if (document.getElementById(`day-${i}`).checked) {
            days.push(i);
        }
    }

    // Parse time values
    const startTime = document.getElementById('window-start-time').value.split(':');
    const endTime = document.getElementById('window-end-time').value.split(':');

    const config = {
        enabled: document.getElementById('window-enabled').value === 'true',
        timezone: document.getElementById('window-timezone').value,
        days_of_week: days,
        start_hour: parseInt(startTime[0]),
        start_minute: parseInt(startTime[1]),
        end_hour: parseInt(endTime[0]),
        end_minute: parseInt(endTime[1])
    };

    try {
        const response = await fetch(`${API_BASE}/api/config/drop-window`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showAlert('Drop window configuration saved successfully', 'success');
        } else {
            showAlert('Failed to save drop window configuration', 'error');
        }
    } catch (error) {
        showAlert('Failed to save configuration', 'error');
    }
});

// Stock form handler
document.getElementById('stock-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const config = {
        enabled: document.getElementById('stock-enabled').checked,
        new_products: document.getElementById('notify-new-products').checked,
        restocked_products: document.getElementById('notify-restocked').checked,
        price_changes: document.getElementById('notify-price-changes').checked,
        out_of_stock: document.getElementById('notify-out-of-stock').checked
    };

    try {
        const response = await fetch(`${API_BASE}/api/config/stock-monitoring`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (response.ok) {
            showAlert('Stock monitoring configuration saved successfully', 'success');
        } else {
            showAlert('Failed to save stock monitoring configuration', 'error');
        }
    } catch (error) {
        showAlert('Failed to save configuration', 'error');
    }
});

// Load initial data
window.addEventListener('DOMContentLoaded', () => {
    loadStatus();
    loadConfig();
    loadDrops();
    loadStockChanges();
});

// Refresh status every 30 seconds
setInterval(loadStatus, 30000);