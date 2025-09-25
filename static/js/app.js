const API_BASE = '';

// Global state
const AppState = {
    config: {},
    status: {},
    loading: new Set(),
    cache: new Map(),
    lastUpdate: {}
};

// Utility Functions
function showAlert(message, type = 'info') {
    // Use new toast system if available, fallback to old system
    if (window.toastManager) {
        return window.toastManager.show(message, type);
    } else {
        const alert = document.getElementById('alert');
        if (!alert) return;

        alert.className = `alert ${type}`;
        alert.textContent = message;
        alert.style.display = 'block';

        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    }
}

function setLoading(elementId, isLoading) {
    const element = document.getElementById(elementId);
    if (!element) return;

    if (isLoading) {
        element.classList.add('loading');
        AppState.loading.add(elementId);

        // Add skeleton for specific elements
        if (elementId.includes('list') || elementId.includes('grid')) {
            showSkeleton(element);
        }
    } else {
        element.classList.remove('loading');
        AppState.loading.delete(elementId);
        hideSkeleton(element);
    }
}

function showSkeleton(container) {
    if (container.querySelector('.skeleton')) return; // Already has skeleton

    const skeletonHTML = `
        <div class="skeleton-content">
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
            <div class="skeleton skeleton-card"></div>
        </div>
    `;

    container.innerHTML = skeletonHTML;
}

function hideSkeleton(container) {
    const skeleton = container.querySelector('.skeleton-content');
    if (skeleton) {
        skeleton.remove();
    }
}

function formatDate(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return 'Never';
    const now = Date.now();
    const diff = now - (timestamp * 1000);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
}

function formatPrice(price) {
    if (!price) return 'N/A';
    return typeof price === 'string' ? price : `$${price.toFixed(2)}`;
}

// API Functions
async function apiCall(endpoint, options = {}) {
    const cacheKey = `${endpoint}:${JSON.stringify(options)}`;

    // Check cache for GET requests
    if (!options.method || options.method === 'GET') {
        const cached = AppState.cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < 30000) { // 30 second cache
            return cached.data;
        }
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();

        // Cache successful GET requests
        if (!options.method || options.method === 'GET') {
            AppState.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
        }

        return data;
    } catch (error) {
        console.error(`API call failed: ${endpoint}`, error);
        throw error;
    }
}

async function loadStatus() {
    try {
        setLoading('system-status', true);
        const data = await apiCall('/api/status');
        AppState.status = data;
        updateSystemStatus(data);
        return data;
    } catch (error) {
        console.error('Failed to load status:', error);
        showAlert('Failed to load system status', 'error');
    } finally {
        setLoading('system-status', false);
    }
}

async function loadConfig() {
    try {
        const data = await apiCall('/api/config');
        AppState.config = data;
        return data;
    } catch (error) {
        console.error('Failed to load config:', error);
        showAlert('Failed to load configuration', 'error');
    }
}

function updateSystemStatus(status) {
    // Update system status indicator
    const statusDot = document.getElementById('system-status');
    if (statusDot) {
        statusDot.className = `status-dot ${status.running ? 'active' : ''}`;
    }

    // Update status text
    const statusText = document.querySelector('.nav-footer .status-text');
    if (statusText) {
        statusText.textContent = status.running ? 'System Active' : 'System Inactive';
    }
}

// Configuration Functions
async function saveRedditConfig(config) {
    try {
        const result = await apiCall('/api/config/reddit', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        showAlert('Reddit configuration saved successfully', 'success');
        AppState.cache.clear(); // Clear cache to reload fresh data
        return result;
    } catch (error) {
        showAlert(`Failed to save Reddit config: ${error.message}`, 'error');
        throw error;
    }
}

async function saveNotificationConfig(config) {
    try {
        const result = await apiCall('/api/config/notifications', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        showAlert('Notification configuration saved successfully', 'success');
        AppState.cache.clear();
        return result;
    } catch (error) {
        showAlert(`Failed to save notification config: ${error.message}`, 'error');
        throw error;
    }
}

async function saveDetectionConfig(config) {
    try {
        const result = await apiCall('/api/config/detection', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        showAlert('Detection configuration saved successfully', 'success');
        AppState.cache.clear();
        return result;
    } catch (error) {
        showAlert(`Failed to save detection config: ${error.message}`, 'error');
        throw error;
    }
}

async function saveDropWindowConfig(config) {
    try {
        const result = await apiCall('/api/config/drop-window', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        showAlert('Drop window configuration saved successfully', 'success');
        AppState.cache.clear();
        return result;
    } catch (error) {
        showAlert(`Failed to save drop window config: ${error.message}`, 'error');
        throw error;
    }
}

async function saveStockMonitoringConfig(config) {
    try {
        const result = await apiCall('/api/config/stock-monitoring', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        showAlert('Stock monitoring configuration saved successfully', 'success');
        AppState.cache.clear();
        return result;
    } catch (error) {
        showAlert(`Failed to save stock monitoring config: ${error.message}`, 'error');
        throw error;
    }
}

// Test Functions
async function testRedditConnection() {
    const form = document.getElementById('reddit-form');
    if (!form) return;

    const config = {
        client_id: document.getElementById('reddit-client-id').value,
        client_secret: document.getElementById('reddit-client-secret').value,
        user_agent: 'FragDropDetector/1.0',
        subreddit: document.getElementById('reddit-subreddit').value,
        check_interval: parseInt(document.getElementById('reddit-interval').value),
        post_limit: 50
    };

    if (!config.client_id || !config.client_secret) {
        showAlert('Please fill in Reddit credentials first', 'warning');
        return;
    }

    try {
        setLoading('reddit-form', true);
        const result = await apiCall('/api/test/reddit', {
            method: 'POST',
            body: JSON.stringify(config)
        });

        if (result.success) {
            showAlert('Reddit connection successful!', 'success');
        } else {
            showAlert(`Reddit connection failed: ${result.message}`, 'error');
        }
    } catch (error) {
        showAlert(`Reddit test failed: ${error.message}`, 'error');
    } finally {
        setLoading('reddit-form', false);
    }
}

async function testAllNotifications() {
    try {
        setLoading('notifications-test', true);
        const results = await apiCall('/api/test/notifications', {
            method: 'POST'
        });

        const messages = [];
        for (const [service, result] of Object.entries(results)) {
            if (result.success) {
                messages.push(`${service}: ✅`);
            } else {
                messages.push(`${service}: ❌ ${result.message}`);
            }
        }

        if (messages.length > 0) {
            showAlert(`Notification test results: ${messages.join(', ')}`, 'info');
        } else {
            showAlert('No notification services configured', 'warning');
        }
    } catch (error) {
        showAlert(`Notification test failed: ${error.message}`, 'error');
    } finally {
        setLoading('notifications-test', false);
    }
}

async function testService(service) {
    // This would test individual services - implementation depends on backend support
    showAlert(`Testing ${service} service...`, 'info');
}

// Data Loading Functions
async function loadRecentDrops(limit = 10) {
    try {
        const drops = await apiCall(`/api/drops?limit=${limit}`);
        return drops;
    } catch (error) {
        console.error('Failed to load drops:', error);
        return [];
    }
}

async function loadStockChanges(limit = 10) {
    try {
        const changes = await apiCall(`/api/stock/changes?limit=${limit}`);
        return changes;
    } catch (error) {
        console.error('Failed to load stock changes:', error);
        return [];
    }
}

async function loadFragrances() {
    try {
        const fragrances = await apiCall('/api/stock/fragrances');
        return fragrances;
    } catch (error) {
        console.error('Failed to load fragrances:', error);
        return {};
    }
}

// Refresh Functions
async function refreshStatus() {
    AppState.cache.clear();
    await loadStatus();

    // Refresh current page data
    const currentPage = window.router?.getCurrentPage();
    if (currentPage === 'dashboard' && typeof refreshDashboard === 'function') {
        refreshDashboard();
    } else if (currentPage === 'monitoring' && typeof refreshMonitoring === 'function') {
        refreshMonitoring();
    }

    showAlert('Status refreshed', 'success');
}

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    // Load initial data
    await Promise.all([
        loadStatus(),
        loadConfig()
    ]);

    // Set up periodic status updates
    setInterval(loadStatus, 30000); // Every 30 seconds

    console.log('FragDropDetector app initialized');
});