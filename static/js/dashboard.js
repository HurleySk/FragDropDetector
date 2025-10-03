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

        // Load watchlist data
        await fetchWatchlistData();

    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

async function fetchWatchlistData() {
    try {
        const response = await apiCall(`/api/stock/fragrances?t=${Date.now()}`);
        if (!response) return;

        const watchlistItems = response.items.filter(item => item.is_watchlisted);
        const inStockCount = watchlistItems.filter(item => item.in_stock).length;

        // Update summary
        const totalElement = document.getElementById('watchlist-total');
        const inStockElement = document.getElementById('watchlist-in-stock');

        if (totalElement) totalElement.textContent = watchlistItems.length;
        if (inStockElement) inStockElement.textContent = inStockCount;

        // Update items list
        const container = document.getElementById('watchlist-items');
        if (!container) return;

        if (watchlistItems.length === 0) {
            container.innerHTML = `
                <div class="watchlist-empty">
                    <div class="watchlist-empty-text">No items in watchlist</div>
                </div>
            `;
        } else {
            container.innerHTML = watchlistItems.slice(0, 5).map(item => `
                <div class="watchlist-item" data-slug="${item.slug}">
                    <div class="watchlist-item-info">
                        <div class="watchlist-item-name">${item.name}</div>
                        <div class="watchlist-item-details">
                            <span class="watchlist-item-price">${item.price || 'N/A'}</span>
                            <span class="watchlist-item-status ${item.in_stock ? 'in-stock' : 'out-of-stock'}">
                                ${item.in_stock ? 'IN STOCK' : 'OUT OF STOCK'}
                            </span>
                        </div>
                    </div>
                    <button class="watchlist-item-remove" onclick="removeFromWatchlist('${item.slug}')" title="Remove">
                        ×
                    </button>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Failed to fetch watchlist data:', error);
    }
}

async function removeFromWatchlist(slug) {
    try {
        console.log('Removing from watchlist:', slug);
        const response = await fetch(`/api/stock/watchlist/remove/${slug}?t=${Date.now()}`, {
            method: 'POST',
            cache: 'no-cache'
        });

        if (response.ok) {
            console.log('Successfully removed from watchlist');
            // Force refresh the watchlist display
            setTimeout(() => fetchWatchlistData(), 100);
            if (window.showAlert) {
                showAlert('Removed from watchlist', 'success');
            }
        } else {
            console.error('Failed to remove from watchlist, response not ok:', response.status);
        }
    } catch (error) {
        console.error('Failed to remove from watchlist:', error);
        if (window.showAlert) {
            showAlert('Failed to remove from watchlist', 'error');
        }
    }
}

// Make function globally accessible
window.removeFromWatchlist = removeFromWatchlist;

function updateDashboardStatus(status) {
    updateRecentActivityCard(status);
    updateRedditMonitorCard(status);
    updateStockMonitorCard(status);
    updateWatchlistAlertsCard(status);
}

async function updateRecentActivityCard(status) {
    const activityText = document.getElementById('recent-activity-text');
    const activitySubtitle = document.getElementById('recent-activity-subtitle');

    if (!activityText || !activitySubtitle) return;

    const monitorRunning = status.monitor_status && status.monitor_status.running;

    if (!monitorRunning) {
        activityText.textContent = 'Offline';
        activityText.className = 'status-value status-disabled';
        activitySubtitle.textContent = 'Monitor stopped';
        return;
    }

    try {
        const [drops, stockChanges] = await Promise.all([
            loadRecentDrops(1),
            loadStockChanges(1)
        ]);

        let mostRecentEvent = null;
        let eventType = '';

        const latestDrop = drops && drops.length > 0 ? drops[0] : null;
        const latestStock = stockChanges && stockChanges.length > 0 ? stockChanges[0] : null;

        const dropTime = latestDrop ? new Date(latestDrop.created_at).getTime() : 0;
        const stockTime = latestStock ? new Date(latestStock.timestamp || latestStock.detected_at).getTime() : 0;

        if (dropTime > stockTime && latestDrop) {
            mostRecentEvent = latestDrop.created_at;
            eventType = 'Last drop';
        } else if (latestStock) {
            mostRecentEvent = latestStock.timestamp || latestStock.detected_at;
            eventType = latestStock.change_type === 'restocked' ? 'Last restock' :
                        latestStock.change_type === 'out_of_stock' ? 'Out of stock' : 'Last change';
        }

        if (mostRecentEvent) {
            const now = Date.now();
            const eventTime = new Date(mostRecentEvent).getTime();
            const daysSince = (now - eventTime) / (1000 * 60 * 60 * 24);

            if (daysSince > 7) {
                activityText.textContent = 'None';
                activityText.className = 'status-value status-disabled';
                activitySubtitle.textContent = 'Last 7 days';
            } else {
                const timeAgo = formatTimeAgo(eventTime / 1000);
                activityText.textContent = timeAgo;
                activityText.className = 'status-value';
                activitySubtitle.textContent = eventType;
            }
        } else {
            activityText.textContent = 'None';
            activityText.className = 'status-value status-disabled';
            activitySubtitle.textContent = 'No events yet';
        }
    } catch (error) {
        console.error('Failed to load recent activity:', error);
        activityText.textContent = 'Error';
        activityText.className = 'status-value status-disabled';
        activitySubtitle.textContent = 'Failed to load';
    }
}

function updateRedditMonitorCard(status) {
    const dropsBadge = document.getElementById('drops-badge');
    const windowStatus = document.getElementById('reddit-window-status');
    const windowSubtitle = document.getElementById('reddit-window-subtitle');

    if (!dropsBadge || !windowStatus || !windowSubtitle) return;

    dropsBadge.textContent = status.drops_detected || 0;

    const monitorRunning = status.monitor_status && status.monitor_status.running;
    const redditWindow = status.reddit_window || {};
    const redditStatus = status.reddit_status || {};

    if (!monitorRunning) {
        windowStatus.textContent = 'Offline';
        windowStatus.className = 'status-value status-disabled';
        windowSubtitle.textContent = 'Monitor stopped';
        return;
    }

    if (!redditStatus.authenticated) {
        windowStatus.textContent = 'Disabled';
        windowStatus.className = 'status-value status-disabled';
        windowSubtitle.textContent = 'Authentication required';
        return;
    }

    if (!redditWindow.enabled) {
        windowStatus.textContent = 'Disabled';
        windowStatus.className = 'status-value status-disabled';
        windowSubtitle.textContent = 'Monitoring disabled';
        return;
    }

    if (redditWindow.active) {
        windowStatus.textContent = 'Active';
        windowStatus.className = 'status-value status-active';
        if (redditWindow.window_end) {
            const endTime = formatTime(redditWindow.window_end);
            windowSubtitle.textContent = `Ends ${endTime}`;
        } else {
            windowSubtitle.textContent = '24/7 monitoring';
        }
    } else {
        windowStatus.textContent = 'Waiting';
        windowStatus.className = 'status-value status-inactive';
        if (redditWindow.next_window_start) {
            const nextTime = formatNextWindow(redditWindow.next_window_start);
            windowSubtitle.textContent = `Next: ${nextTime}`;
        } else {
            windowSubtitle.textContent = 'No schedule set';
        }
    }
}

function updateStockMonitorCard(status) {
    const fragrancesBadge = document.getElementById('fragrances-badge');
    const windowStatus = document.getElementById('stock-window-status');
    const windowSubtitle = document.getElementById('stock-window-subtitle');

    if (!fragrancesBadge || !windowStatus || !windowSubtitle) return;

    fragrancesBadge.textContent = status.fragrances_tracked || 0;

    const monitorRunning = status.monitor_status && status.monitor_status.running;
    const stockWindow = status.stock_window || {};

    if (!monitorRunning) {
        windowStatus.textContent = 'Offline';
        windowStatus.className = 'status-value status-disabled';
        windowSubtitle.textContent = 'Monitor stopped';
        return;
    }

    if (!stockWindow.enabled) {
        windowStatus.textContent = 'Disabled';
        windowStatus.className = 'status-value status-disabled';
        windowSubtitle.textContent = 'Monitoring disabled';
        return;
    }

    if (stockWindow.mode === '24/7') {
        windowStatus.textContent = 'Monitoring';
        windowStatus.className = 'status-value status-active';
        windowSubtitle.textContent = '24/7 active';
        return;
    }

    if (stockWindow.active) {
        windowStatus.textContent = 'Active';
        windowStatus.className = 'status-value status-active';
        if (stockWindow.window_end) {
            const endTime = formatTime(stockWindow.window_end);
            windowSubtitle.textContent = `Ends ${endTime}`;
        } else {
            windowSubtitle.textContent = 'Active now';
        }
    } else {
        windowStatus.textContent = 'Waiting';
        windowStatus.className = 'status-value status-inactive';
        if (stockWindow.next_window_start) {
            const nextTime = formatNextWindow(stockWindow.next_window_start);
            windowSubtitle.textContent = `Next: ${nextTime}`;
        } else {
            windowSubtitle.textContent = 'No schedule set';
        }
    }
}

function updateWatchlistAlertsCard(status) {
    const changesBadge = document.getElementById('stock-changes-badge');
    const alertCount = document.getElementById('watchlist-alert-count');
    const alertSubtitle = document.getElementById('watchlist-alert-subtitle');

    if (!changesBadge || !alertCount || !alertSubtitle) return;

    changesBadge.textContent = status.recent_stock_changes || 0;

    const watchlistAlerts = status.watchlist_alerts || {};
    const outOfStock = watchlistAlerts.out_of_stock || 0;

    alertCount.textContent = outOfStock;

    if (outOfStock > 0) {
        alertCount.className = 'status-value status-warning';
        alertSubtitle.textContent = `${outOfStock} ${outOfStock === 1 ? 'item needs' : 'items need'} attention`;
    } else {
        alertCount.className = 'status-value status-success';
        alertSubtitle.textContent = 'All watchlist items in stock';
    }
}

function formatTime(isoString) {
    if (!isoString) return '--';
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
            timeZoneName: 'short'
        });
    } catch (e) {
        return '--';
    }
}

function formatNextWindow(isoString) {
    if (!isoString) return '--';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = date - now;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 1) {
            const diffMins = Math.floor(diffMs / (1000 * 60));
            return `${diffMins} min`;
        } else if (diffHours < 24) {
            return `${diffHours}h`;
        } else if (diffDays < 7) {
            const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
            const time = date.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            });
            return `${dayName} ${time}`;
        } else {
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit'
            });
        }
    } catch (e) {
        return '--';
    }
}

function navigateToConfigTab(tabName) {
    if (window.router && typeof window.router.navigateTo === 'function') {
        window.router.navigateTo('configuration');
        setTimeout(() => {
            const tabBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
            if (tabBtn) {
                tabBtn.click();
            }
        }, 100);
    }
}

function navigateToInventoryWatchlist() {
    if (window.router && typeof window.router.navigateTo === 'function') {
        window.router.navigateTo('inventory');
        setTimeout(() => {
            if (window.InventoryManager) {
                window.InventoryManager.watchlistOnly = true;
                const watchlistToggle = document.getElementById('watchlist-toggle');
                if (watchlistToggle) {
                    watchlistToggle.classList.add('active');
                }
                if (typeof window.InventoryManager.loadInventory === 'function') {
                    window.InventoryManager.loadInventory();
                }
            }
        }, 100);
    }
}

window.navigateToConfigTab = navigateToConfigTab;
window.navigateToInventoryWatchlist = navigateToInventoryWatchlist;

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
        // Check Reddit API health and authentication status
        try {
            const status = await apiCall('/api/status');
            const redditStatus = status.reddit_status || {};

            if (!status.reddit_status) {
                // Old API version or missing reddit_status
                updateHealthIndicator('reddit', 'warning', 'Restart web server for auth status');
            } else if (redditStatus.authenticated) {
                updateHealthIndicator('reddit', 'healthy', `Authenticated as u/${redditStatus.username}`);
            } else {
                updateHealthIndicator('reddit', 'warning', 'Authentication required - monitoring disabled');
            }
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
            const response = await apiCall('/api/stock/fragrances');
            const count = response?.total || 0;
            const watchlistCount = response?.watchlist_slugs?.length || 0;
            if (count > 0) {
                const statusText = watchlistCount > 0
                    ? `${count} products (${watchlistCount} watched)`
                    : `${count} products tracked`;
                updateHealthIndicator('monitoring', 'healthy', statusText);
            } else {
                updateHealthIndicator('monitoring', 'warning', 'No products tracked');
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