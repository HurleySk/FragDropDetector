/**
 * Dashboard Functions
 * Handles button clicks and interactions for the dashboard
 */

// Test individual notification services
async function testService(serviceType) {
    const button = event.target;
    const originalText = button.textContent;

    // Show loading state
    button.disabled = true;
    button.textContent = 'Testing...';

    try {
        const response = await fetch(`/api/test/${serviceType}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const result = await response.json();

        if (response.ok) {
            showAlert('success', `${serviceType} test notification sent successfully!`);
        } else {
            showAlert('error', `${serviceType} test failed: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Test service error:', error);
        showAlert('error', `Failed to test ${serviceType}: Network error`);
    } finally {
        // Restore button state
        button.disabled = false;
        button.textContent = originalText;
    }
}

// Test all notification services
async function testAllNotifications() {
    const button = event.target;
    const originalText = button.textContent;

    // Show loading state
    button.disabled = true;
    button.textContent = 'Testing All...';

    try {
        const response = await fetch('/api/test/all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const result = await response.json();

        if (response.ok) {
            showAlert('success', 'Test notifications sent to all configured services!');
        } else {
            showAlert('error', `Test failed: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Test all notifications error:', error);
        showAlert('error', 'Failed to test notifications: Network error');
    } finally {
        // Restore button state
        button.disabled = false;
        button.textContent = originalText;
    }
}

// Refresh system status
async function refreshStatus() {
    const button = event.target;
    const originalText = button.textContent;

    // Show loading state
    button.disabled = true;
    button.textContent = 'Refreshing...';

    try {
        const response = await fetch('/api/status', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const status = await response.json();

        if (response.ok) {
            updateDashboardStats(status);
            showAlert('success', 'Status refreshed successfully!');
        } else {
            showAlert('error', `Failed to refresh status: ${status.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Refresh status error:', error);
        showAlert('error', 'Failed to refresh status: Network error');
    } finally {
        // Restore button state
        button.disabled = false;
        button.textContent = originalText;
    }
}

// Navigate to different pages
function navigateToPage(page) {
    if (window.router && typeof window.router.navigateTo === 'function') {
        window.router.navigateTo(page);
    } else {
        // Fallback: show the page content directly
        const pages = ['dashboard', 'configuration', 'monitoring'];

        pages.forEach(p => {
            const element = document.getElementById(`${p}-content`);
            if (element) {
                element.classList.toggle('hidden', p !== page);
            }
        });

        // Update navigation active state
        document.querySelectorAll('.nav-item').forEach(item => {
            const itemPage = item.getAttribute('data-page');
            item.classList.toggle('active', itemPage === page);
        });
    }
}

// Update dashboard statistics
function updateDashboardStats(status) {
    const stats = {
        'drops-count': status.drops_detected || 0,
        'fragrances-count': status.fragrances_tracked || 0,
        'stock-changes-count': status.stock_changes || 0,
        'next-window': status.next_window || '--'
    };

    Object.entries(stats).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });

    // Update health indicators
    updateHealthIndicators(status.health || {});
}

// Update health status indicators
function updateHealthIndicators(health) {
    const healthMappings = {
        'reddit-health': health.reddit || 'unknown',
        'database-health': health.database || 'unknown',
        'notifications-health': health.notifications || 'unknown',
        'monitoring-health': health.monitoring || 'unknown'
    };

    Object.entries(healthMappings).forEach(([id, status]) => {
        const element = document.getElementById(id);
        if (element) {
            element.className = 'health-indicator';

            if (status === 'healthy' || status === 'online') {
                element.classList.add('healthy');
            } else if (status === 'warning' || status === 'partial') {
                element.classList.add('warning');
            } else {
                element.classList.add('unhealthy');
            }
        }
    });
}

// Show alert messages
function showAlert(type, message) {
    const alertElement = document.getElementById('alert');
    if (alertElement) {
        alertElement.className = `alert ${type}`;
        alertElement.textContent = message;
        alertElement.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            alertElement.style.display = 'none';
        }, 5000);
    }
}

// Load dashboard data on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load initial status
    refreshStatus();

    // Set up periodic status updates (every 30 seconds)
    setInterval(refreshStatus, 30000);
});

// Export functions for global access
window.testService = testService;
window.testAllNotifications = testAllNotifications;
window.refreshStatus = refreshStatus;
window.navigateToPage = navigateToPage;