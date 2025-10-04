/**
 * Dashboard Status Card Updates
 */

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

function updateStatusTrends(status) {
    const windowStatus = document.getElementById('window-status');
    if (windowStatus) {
        windowStatus.textContent = status.running ? 'Active' : 'Inactive';
        windowStatus.className = `status-trend ${status.running ? 'window-active' : 'window-inactive'}`;
    }
}
