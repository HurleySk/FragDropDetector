/**
 * Dashboard Main Controller
 * Orchestrates all dashboard modules
 */

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

function setupDashboardRefresh() {
    dashboardRefreshInterval = setInterval(() => {
        if (window.router?.getCurrentPage() === 'dashboard') {
            loadDashboardData();
        }
    }, 60000);
}

function refreshDashboard() {
    AppState.cache.clear();
    loadDashboardData();
}
