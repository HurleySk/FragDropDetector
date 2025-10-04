/**
 * Dashboard Data Loading
 */

async function loadDashboardData() {
    try {
        const status = await loadStatus();
        updateDashboardStatus(status);

        await updateHealthChecks();

        await loadRecentActivity();

        await updateNotificationServicesStatus();

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

        const totalElement = document.getElementById('watchlist-total');
        const inStockElement = document.getElementById('watchlist-in-stock');

        if (totalElement) totalElement.textContent = watchlistItems.length;
        if (inStockElement) inStockElement.textContent = inStockCount;

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
        await WatchlistService.removeItem(slug);
        console.log('Successfully removed from watchlist');
        setTimeout(() => fetchWatchlistData(), 100);
        if (window.showAlert) {
            showAlert('Removed from watchlist', 'success');
        }
    } catch (error) {
        console.error('Failed to remove from watchlist:', error);
        if (window.showAlert) {
            showAlert('Failed to remove from watchlist', 'error');
        }
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

window.removeFromWatchlist = removeFromWatchlist;
