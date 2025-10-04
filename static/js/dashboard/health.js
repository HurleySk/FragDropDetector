/**
 * Dashboard Health Check Functions
 */

async function updateHealthChecks() {
    try {
        // Check Reddit API health and authentication status
        try {
            const status = await apiCall('/api/status');
            const redditStatus = status.reddit_status || {};

            if (!status.reddit_status) {
                updateHealthIndicator('reddit', 'warning', 'Restart web server for auth status');
            } else if (redditStatus.authenticated) {
                updateHealthIndicator('reddit', 'healthy', `Authenticated as u/${redditStatus.username}`);
            } else {
                updateHealthIndicator('reddit', 'warning', 'Authentication required - monitoring disabled');
            }
        } catch (error) {
            updateHealthIndicator('reddit', 'unhealthy', 'Connection Failed');
        }

        // Check database health
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

async function updateNotificationServicesStatus() {
    try {
        const config = AppState.config || await loadConfig();

        updateServiceStatus('pushover',
            config.notifications?.pushover_app_token && config.notifications?.pushover_user_key);

        updateServiceStatus('discord',
            config.notifications?.discord_webhook_url);

        updateServiceStatus('email',
            false);

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
