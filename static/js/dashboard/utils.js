/**
 * Dashboard Utility Functions
 */

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
