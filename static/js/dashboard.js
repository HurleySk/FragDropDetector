// Dashboard-specific functionality

let dashboardRefreshInterval = null;

function initializeDashboard() {
    loadDashboardData();
    setupDashboardRefresh();
}

function cleanupDashboard() {
    if (dashboardRefreshInterval) {
        clearInterval(dashboardRefreshInterval);
        dashboardRefreshInterval = null;
    }
}

async function loadDashboardData() {
    try {
        // Load status and update dashboard
        const status = await loadStatus();
        updateDashboardStatus(status);

        // Update health checks
        await updateHealthChecks();

        // Load recent activity preview
        await loadRecentActivity();

        // Update notification services status
        await updateNotificationServicesStatus();

    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

function updateDashboardStatus(status) {
    // Update status cards
    document.getElementById('drops-count').textContent = status.drops_detected || 0;
    document.getElementById('fragrances-count').textContent = status.fragrances_tracked || 0;
    document.getElementById('stock-changes-count').textContent = status.recent_stock_changes || 0;

    // Update next window
    const nextWindow = document.getElementById('next-window');
    if (status.next_window) {
        const nextDate = new Date(status.next_window);
        const now = new Date();
        const hours = Math.floor((nextDate - now) / (1000 * 60 * 60));
        nextWindow.textContent = hours > 0 ? `${hours}h` : 'Soon';
    } else {
        nextWindow.textContent = 'Active';
    }

    // Update trends (placeholder for future enhancement)
    updateStatusTrends(status);
}

function updateStatusTrends(status) {
    // This would show trend indicators - for now just show status
    const windowStatus = document.getElementById('window-status');
    if (windowStatus) {
        windowStatus.textContent = status.running ? 'Active' : 'Inactive';
        windowStatus.className = `status-trend ${status.running ? 'window-active' : 'window-inactive'}`;
    }
}

async function updateNotificationServicesStatus() {
    try {
        const config = AppState.config || await loadConfig();

        // Update Pushover status
        updateServiceStatus('pushover',
            config.notifications?.pushover_app_token && config.notifications?.pushover_user_key);

        // Update Discord status
        updateServiceStatus('discord',
            config.notifications?.discord_webhook_url);

        // Update Email status
        updateServiceStatus('email',
            false); // Email config not exposed in current API

    } catch (error) {
        console.error('Failed to update notification services status:', error);
    }
}

function updateServiceStatus(service, enabled) {
    const serviceElement = document.getElementById(`${service}-service`);
    const statusElement = serviceElement?.querySelector('.service-status');

    if (statusElement) {
        statusElement.textContent = enabled ? 'Active' : 'Disabled';
        statusElement.className = `service-status ${enabled ? 'active' : 'disabled'}`;
    }
}

async function loadRecentActivity() {
    try {
        const [drops, stockChanges] = await Promise.all([
            loadRecentDrops(3),
            loadStockChanges(3)
        ]);

        displayRecentActivity(drops, stockChanges);
    } catch (error) {
        console.error('Failed to load recent activity:', error);
        displayActivityError();
    }
}

function displayRecentActivity(drops, stockChanges) {
    const container = document.getElementById('recent-activity-list');
    if (!container) return;

    // Combine and sort by timestamp
    const allActivity = [
        ...drops.map(drop => ({ ...drop, type: 'drop' })),
        ...stockChanges.map(change => ({ ...change, type: 'stock' }))
    ].sort((a, b) => {
        const aTime = a.created_at || a.timestamp || 0;
        const bTime = b.created_at || b.timestamp || 0;
        return bTime - aTime;
    }).slice(0, 5);

    if (allActivity.length === 0) {
        container.innerHTML = `
            <div class="activity-placeholder">
                <div class="placeholder-text">No recent activity</div>
            </div>
        `;
        return;
    }

    container.innerHTML = allActivity.map(item => {
        if (item.type === 'drop') {
            return `
                <div class="activity-item drop-activity">
                    <div class="activity-icon">🎯</div>
                    <div class="activity-content">
                        <div class="activity-title">${item.title || 'Drop Detected'}</div>
                        <div class="activity-meta">
                            <span class="activity-confidence">Confidence: ${Math.round((item.confidence || 0) * 100)}%</span>
                            <span class="activity-time">${formatTimeAgo(item.created_at)}</span>
                        </div>
                    </div>
                    ${item.url ? `<a href="${item.url}" target="_blank" class="activity-link">View</a>` : ''}
                </div>
            `;
        } else {
            return `
                <div class="activity-item stock-activity">
                    <div class="activity-icon">📈</div>
                    <div class="activity-content">
                        <div class="activity-title">${item.change_type || 'Stock Change'}</div>
                        <div class="activity-meta">
                            <span class="activity-fragrance">${item.fragrance_name || 'Unknown'}</span>
                            <span class="activity-time">${formatTimeAgo(item.timestamp)}</span>
                        </div>
                    </div>
                </div>
            `;
        }
    }).join('');
}

function displayActivityError() {
    const container = document.getElementById('recent-activity-list');
    if (!container) return;

    container.innerHTML = `
        <div class="activity-placeholder">
            <div class="placeholder-text">Failed to load recent activity</div>
        </div>
    `;
}

function setupDashboardRefresh() {
    // Refresh dashboard data every 60 seconds
    dashboardRefreshInterval = setInterval(() => {
        if (window.router?.getCurrentPage() === 'dashboard') {
            loadDashboardData();
        }
    }, 60000);
}

async function updateHealthChecks() {
    try {
        // Check Reddit API health (via config endpoint)
        try {
            await apiCall('/api/config');
            updateHealthIndicator('reddit', 'healthy', 'Connected');
        } catch (error) {
            updateHealthIndicator('reddit', 'unhealthy', 'Connection Failed');
        }

        // Check database health (via status endpoint)
        try {
            await apiCall('/api/status');
            updateHealthIndicator('database', 'healthy', 'Connected');
        } catch (error) {
            updateHealthIndicator('database', 'unhealthy', 'Connection Failed');
        }

        // Check notifications health
        try {
            const config = AppState.config || await loadConfig();
            const hasNotifications = config.notifications?.pushover_app_token ||
                                   config.notifications?.discord_webhook_url ||
                                   config.notifications?.email_sender;

            if (hasNotifications) {
                updateHealthIndicator('notifications', 'healthy', 'Configured');
            } else {
                updateHealthIndicator('notifications', 'warning', 'Not Configured');
            }
        } catch (error) {
            updateHealthIndicator('notifications', 'unhealthy', 'Error');
        }

        // Check stock monitoring health
        try {
            const fragrances = await apiCall('/api/stock/fragrances');
            const count = Object.keys(fragrances || {}).length;
            if (count > 0) {
                updateHealthIndicator('monitoring', 'healthy', `Tracking ${count} items`);
            } else {
                updateHealthIndicator('monitoring', 'warning', 'No items tracked');
            }
        } catch (error) {
            updateHealthIndicator('monitoring', 'unhealthy', 'Service Error');
        }

    } catch (error) {
        console.error('Failed to update health checks:', error);
    }
}

function updateHealthIndicator(service, status, message) {
    const indicator = document.getElementById(`${service}-health`);
    const statusText = document.getElementById(`${service}-status`);

    if (indicator) {
        indicator.className = `health-indicator ${status}`;
    }

    if (statusText) {
        statusText.textContent = message;
    }
}

function refreshDashboard() {
    AppState.cache.clear();
    loadDashboardData();
}