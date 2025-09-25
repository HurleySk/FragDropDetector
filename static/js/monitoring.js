// Monitoring page functionality

let monitoringRefreshInterval = null;

function initializeMonitoring() {
    setupMonitoringTabs();
    loadMonitoringData();
    setupMonitoringRefresh();
}

function cleanupMonitoring() {
    if (monitoringRefreshInterval) {
        clearInterval(monitoringRefreshInterval);
        monitoringRefreshInterval = null;
    }
}

function setupMonitoringTabs() {
    const tabButtons = document.querySelectorAll('.data-tabs .tab-btn');
    const tabContents = document.querySelectorAll('.data-tabs .tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');

            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update active tab content
            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === `${targetTab}-tab`);
            });

            // Load data for active tab
            loadTabData(targetTab);
        });
    });
}

async function loadMonitoringData() {
    // Load all tabs data
    await Promise.all([
        loadTabData('drops'),
        loadTabData('stock'),
        loadTabData('fragrances')
    ]);
}

async function loadTabData(tab) {
    switch (tab) {
        case 'drops':
            await refreshDrops();
            break;
        case 'stock':
            await refreshStockChanges();
            break;
        case 'fragrances':
            await refreshFragrances();
            break;
    }
}

async function refreshDrops() {
    const limit = parseInt(document.getElementById('drops-limit')?.value || '10');
    const container = document.getElementById('drops-list');

    if (!container) return;

    try {
        setLoading('drops-list', true);
        const drops = await loadRecentDrops(limit);
        displayDrops(drops, container);
    } catch (error) {
        console.error('Failed to load drops:', error);
        displayError(container, 'Failed to load drops');
    } finally {
        setLoading('drops-list', false);
    }
}

async function refreshStockChanges() {
    const limit = parseInt(document.getElementById('stock-limit')?.value || '10');
    const container = document.getElementById('stock-changes-list');

    if (!container) return;

    try {
        setLoading('stock-changes-list', true);
        const changes = await loadStockChanges(limit);
        displayStockChanges(changes, container);
    } catch (error) {
        console.error('Failed to load stock changes:', error);
        displayError(container, 'Failed to load stock changes');
    } finally {
        setLoading('stock-changes-list', false);
    }
}

async function refreshFragrances() {
    const container = document.getElementById('fragrances-grid');

    if (!container) return;

    try {
        setLoading('fragrances-grid', true);
        const fragrances = await loadFragrances();
        displayFragrances(fragrances, container);
    } catch (error) {
        console.error('Failed to load fragrances:', error);
        displayError(container, 'Failed to load fragrances');
    } finally {
        setLoading('fragrances-grid', false);
    }
}

function displayDrops(drops, container) {
    if (!drops || drops.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🎯</div>
                <div class="empty-state-title">No Drops Found</div>
                <div class="empty-state-description">
                    No fragrance drops have been detected yet. Once the monitor is running and finds drops, they'll appear here.
                </div>
                <button class="empty-state-action" onclick="navigateToPage('configuration')">
                    ⚙️ Configure Detection
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = drops.map(drop => `
        <div class="data-item drop-item">
            <div class="item-header">
                <div class="item-title">${escapeHtml(drop.title || 'Untitled Drop')}</div>
                <div class="item-meta">
                    <span class="confidence-badge ${getConfidenceClass(drop.confidence)}">
                        ${Math.round((drop.confidence || 0) * 100)}%
                    </span>
                    <span class="time-badge">${formatTimeAgo(drop.created_at)}</span>
                </div>
            </div>

            <div class="item-content">
                <div class="item-details">
                    <div class="detail-item">
                        <span class="detail-label">Author:</span>
                        <span class="detail-value">${escapeHtml(drop.author || 'Unknown')}</span>
                    </div>
                    ${drop.subreddit ? `
                        <div class="detail-item">
                            <span class="detail-label">Subreddit:</span>
                            <span class="detail-value">r/${escapeHtml(drop.subreddit)}</span>
                        </div>
                    ` : ''}
                </div>

                ${drop.url ? `
                    <div class="item-actions">
                        <a href="${escapeHtml(drop.url)}" target="_blank" class="action-link">
                            View Post →
                        </a>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function displayStockChanges(changes, container) {
    if (!changes || changes.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📈</div>
                <div class="empty-state-title">No Stock Changes</div>
                <div class="empty-state-description">
                    No stock changes have been detected yet. Stock monitoring will track inventory changes and display them here.
                </div>
                <button class="empty-state-action" onclick="navigateToPage('configuration')">
                    📊 Configure Stock Monitor
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = changes.map(change => `
        <div class="data-item stock-change-item">
            <div class="item-header">
                <div class="item-title">${escapeHtml(change.fragrance_name || 'Unknown Fragrance')}</div>
                <div class="item-meta">
                    <span class="change-badge ${change.change_type}">${getChangeTypeLabel(change.change_type)}</span>
                    <span class="time-badge">${formatTimeAgo(change.timestamp)}</span>
                </div>
            </div>

            <div class="item-content">
                <div class="change-details">
                    ${change.old_value && change.new_value ? `
                        <div class="change-values">
                            <span class="old-value">${escapeHtml(change.old_value)}</span>
                            <span class="change-arrow">→</span>
                            <span class="new-value">${escapeHtml(change.new_value)}</span>
                        </div>
                    ` : change.new_value ? `
                        <div class="new-value-only">${escapeHtml(change.new_value)}</div>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function displayFragrances(fragrances, container) {
    const fragranceList = Object.entries(fragrances || {});

    if (fragranceList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🧴</div>
                <div class="empty-state-title">No Fragrances Tracked</div>
                <div class="empty-state-description">
                    Stock monitoring hasn't started yet or no fragrances have been found. Enable stock monitoring to track inventory.
                </div>
                <button class="empty-state-action" onclick="navigateToPage('configuration')">
                    🔧 Enable Stock Monitoring
                </button>
            </div>
        `;
        return;
    }

    // Apply current filters
    const filteredFragrances = applyFragranceFilters(fragranceList);

    container.innerHTML = `
        <div class="fragrance-list">
            ${filteredFragrances.map(([slug, fragrance]) => `
                <div class="fragrance-card ${fragrance.in_stock ? 'in-stock' : 'out-of-stock'}">
                    <div class="fragrance-header">
                        <div class="fragrance-name">${escapeHtml(fragrance.name)}</div>
                        <div class="stock-indicator">
                            <span class="stock-status ${fragrance.in_stock ? 'in-stock' : 'out-of-stock'}">
                                ${fragrance.in_stock ? 'In Stock' : 'Out of Stock'}
                            </span>
                        </div>
                    </div>

                    <div class="fragrance-details">
                        <div class="price">${formatPrice(fragrance.price)}</div>
                        ${fragrance.last_updated ? `
                            <div class="last-updated">Updated ${formatTimeAgo(fragrance.last_updated)}</div>
                        ` : ''}
                    </div>

                    ${fragrance.url ? `
                        <div class="fragrance-actions">
                            <a href="https://www.montagneparfums.com${fragrance.url}" target="_blank" class="view-link">
                                View Product
                            </a>
                        </div>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

function applyFragranceFilters(fragrances) {
    let filtered = [...fragrances];

    // Apply availability filter
    const availabilityFilter = document.getElementById('availability-filter')?.value;
    if (availabilityFilter === 'in_stock') {
        filtered = filtered.filter(([_, fragrance]) => fragrance.in_stock);
    } else if (availabilityFilter === 'out_of_stock') {
        filtered = filtered.filter(([_, fragrance]) => !fragrance.in_stock);
    }

    // Apply sorting
    const sortFilter = document.getElementById('sort-filter')?.value;
    switch (sortFilter) {
        case 'name':
            filtered.sort(([_, a], [__, b]) => a.name.localeCompare(b.name));
            break;
        case 'price_asc':
            filtered.sort(([_, a], [__, b]) => parseFloat(a.price || 0) - parseFloat(b.price || 0));
            break;
        case 'price_desc':
            filtered.sort(([_, a], [__, b]) => parseFloat(b.price || 0) - parseFloat(a.price || 0));
            break;
        case 'updated':
            filtered.sort(([_, a], [__, b]) => (b.last_updated || 0) - (a.last_updated || 0));
            break;
    }

    return filtered;
}

function filterFragrances() {
    refreshFragrances();
}

function sortFragrances() {
    refreshFragrances();
}

function displayError(container, message) {
    container.innerHTML = `
        <div class="data-placeholder error">
            <div class="placeholder-icon">⚠️</div>
            <div class="placeholder-text">${escapeHtml(message)}</div>
        </div>
    `;
}

function getConfidenceClass(confidence) {
    const score = (confidence || 0) * 100;
    if (score >= 80) return 'high';
    if (score >= 60) return 'medium';
    return 'low';
}

function getChangeTypeLabel(changeType) {
    const labels = {
        'new': 'New Product',
        'restocked': 'Restocked',
        'price_change': 'Price Change',
        'out_of_stock': 'Out of Stock'
    };
    return labels[changeType] || changeType;
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function setupMonitoringRefresh() {
    // Auto-refresh data every 2 minutes when on monitoring page
    monitoringRefreshInterval = setInterval(() => {
        if (window.router?.getCurrentPage() === 'monitoring') {
            const activeTab = document.querySelector('.data-tabs .tab-btn.active')?.getAttribute('data-tab');
            if (activeTab) {
                loadTabData(activeTab);
            }
        }
    }, 120000); // 2 minutes
}

function refreshMonitoring() {
    AppState.cache.clear();
    loadMonitoringData();
}