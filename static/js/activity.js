// Activity page functionality

let activityCurrentFilter = 'all';
let activityCurrentPage = 1;
let activityPageSize = 20;
let activityHasMore = true;

function initializeActivity() {
    setupActivityFilters();
    loadActivityTimeline();
}

function cleanupActivity() {
    // Cleanup if needed when leaving page
}

function setupActivityFilters() {
    const filterTabs = document.querySelectorAll('.filter-tab');

    filterTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            filterTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            activityCurrentFilter = this.dataset.filter;
            activityCurrentPage = 1;
            activityHasMore = true;
            loadActivityTimeline();
        });
    });

    const loadMoreBtn = document.getElementById('load-more-activity');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', loadMoreActivity);
    }
}

async function loadActivityTimeline() {
    const timeline = document.getElementById('activity-timeline');
    if (!timeline) return;

    timeline.innerHTML = `
        <div class="loading-placeholder">
            <div class="loading-spinner"></div>
            <p>Loading activity...</p>
        </div>
    `;

    try {
        const [drops, stockChanges] = await Promise.all([
            activityCurrentFilter !== 'stock' ? loadRecentDrops(100) : Promise.resolve([]),
            activityCurrentFilter !== 'drops' ? loadStockChanges(100) : Promise.resolve([])
        ]);

        const combinedActivity = combineAndSortActivity(drops, stockChanges);
        displayActivityTimeline(combinedActivity);
    } catch (error) {
        console.error('Failed to load activity timeline:', error);
        timeline.innerHTML = `
            <div class="empty-state">
                <p class="empty-state-message">Failed to load activity</p>
            </div>
        `;
    }
}

function combineAndSortActivity(drops, stockChanges) {
    const allActivity = [
        ...(drops || []).map(drop => ({
            ...drop,
            type: 'drop',
            timestamp: window.DateUtils.toUnixMillis(drop.created_at)
        })),
        ...(stockChanges || []).map(change => ({
            ...change,
            type: 'stock',
            timestamp: window.DateUtils.toUnixMillis(change.detected_at)
        }))
    ];

    return allActivity.sort((a, b) => b.timestamp - a.timestamp);
}

function displayActivityTimeline(activity) {
    const timeline = document.getElementById('activity-timeline');
    if (!timeline) return;

    if (activity.length === 0) {
        timeline.innerHTML = `
            <div class="empty-state">
                <p class="empty-state-message">No activity found</p>
            </div>
        `;
        return;
    }

    const paginatedActivity = activity.slice(0, activityCurrentPage * activityPageSize);
    const groupedActivity = groupActivityByDate(paginatedActivity);

    let html = '';
    for (const [dateLabel, events] of Object.entries(groupedActivity)) {
        html += `
            <div class="activity-date-group">
                <h3 class="activity-date-label">${dateLabel}</h3>
                <div class="activity-events">
                    ${events.map(event => renderActivityEvent(event)).join('')}
                </div>
            </div>
        `;
    }

    timeline.innerHTML = html;

    const loadMoreBtn = document.getElementById('load-more-activity');
    if (loadMoreBtn) {
        if (paginatedActivity.length >= activity.length) {
            loadMoreBtn.style.display = 'none';
            activityHasMore = false;
        } else {
            loadMoreBtn.style.display = 'block';
            activityHasMore = true;
        }
    }
}

function groupActivityByDate(activity) {
    const groups = {};
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    activity.forEach(event => {
        const eventDate = new Date(event.timestamp);
        const eventDay = new Date(eventDate.getFullYear(), eventDate.getMonth(), eventDate.getDate());

        let label;
        if (eventDay.getTime() === today.getTime()) {
            label = 'Today';
        } else if (eventDay.getTime() === yesterday.getTime()) {
            label = 'Yesterday';
        } else if ((now - eventDay) < 7 * 24 * 60 * 60 * 1000) {
            label = eventDate.toLocaleDateString('en-US', { weekday: 'long' });
        } else {
            label = eventDate.toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: eventDate.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        }

        if (!groups[label]) {
            groups[label] = [];
        }
        groups[label].push(event);
    });

    return groups;
}

function renderActivityEvent(event) {
    if (event.type === 'drop') {
        return renderDropEvent(event);
    } else {
        return renderStockEvent(event);
    }
}

function renderDropEvent(drop) {
    const time = window.DateUtils.formatDateTime(drop.timestamp);

    const confidencePercent = Math.round((drop.confidence || 0) * 100);
    const confidenceClass = confidencePercent >= 80 ? 'high' : confidencePercent >= 60 ? 'medium' : 'low';

    return `
        <div class="activity-event drop-event" data-event-id="${drop.id}" data-event-type="drop">
            <div class="activity-event-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="10" cy="10" r="8" fill="currentColor" opacity="0.2"/>
                    <path d="M10 6v4m0 0v4m0-4h4m-4 0H6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </div>
            <div class="activity-event-content">
                <div class="activity-event-header">
                    <h4 class="activity-event-title">Drop Detected</h4>
                    <span class="activity-event-time">${time}</span>
                </div>
                <p class="activity-event-description">${escapeHtml(drop.title)}</p>
                <div class="activity-event-meta">
                    <span class="confidence-badge ${confidenceClass}">${confidencePercent}% confidence</span>
                    ${drop.author ? `<span class="author">by u/${escapeHtml(drop.author)}</span>` : ''}
                    ${drop.url ? `<a href="${escapeHtml(drop.url)}" target="_blank" class="btn btn-primary btn-sm">View →</a>` : ''}
                </div>
            </div>
            <button class="activity-delete-btn" onclick="deleteActivity(${drop.id}, 'drop')" title="Delete">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6 2h4M2 4h12M13 4l-.5 8a2 2 0 01-2 1.9H5.5a2 2 0 01-2-1.9L3 4m3 3v4m4-4v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>
        </div>
    `;
}

function renderStockEvent(change) {
    const time = window.DateUtils.formatDateTime(change.timestamp);

    const changeTypeLabel = {
        'restocked': 'Restocked',
        'out_of_stock': 'Out of Stock',
        'price_change': 'Price Changed',
        'new_product': 'New Product'
    }[change.change_type] || 'Stock Change';

    const changeTypeClass = {
        'restocked': 'restock',
        'out_of_stock': 'out-stock',
        'price_change': 'price-change',
        'new_product': 'new-product'
    }[change.change_type] || 'change';

    return `
        <div class="activity-event stock-event ${changeTypeClass}" data-event-id="${change.id}" data-event-type="stock">
            <div class="activity-event-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="10" cy="10" r="8" fill="currentColor" opacity="0.2"/>
                    <path d="M10 14V6m0 0L7 9m3-3l3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <div class="activity-event-content">
                <div class="activity-event-header">
                    <h4 class="activity-event-title">${changeTypeLabel}</h4>
                    <span class="activity-event-time">${time}</span>
                </div>
                <p class="activity-event-description">${escapeHtml(change.fragrance_name)}</p>
                <div class="activity-event-meta">
                    ${change.new_value ? `<span class="value-change">${escapeHtml(change.new_value)}</span>` : ''}
                    ${change.product_url ? `<a href="${escapeHtml(change.product_url)}" target="_blank" class="btn btn-primary btn-sm">View →</a>` : ''}
                </div>
            </div>
            <button class="activity-delete-btn" onclick="deleteActivity(${change.id}, 'stock')" title="Delete">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6 2h4M2 4h12M13 4l-.5 8a2 2 0 01-2 1.9H5.5a2 2 0 01-2-1.9L3 4m3 3v4m4-4v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>
        </div>
    `;
}

function loadMoreActivity() {
    activityCurrentPage++;
    loadActivityTimeline();
}

async function deleteActivity(id, type) {
    if (!confirm('Are you sure you want to delete this activity?')) {
        return;
    }

    const eventElement = document.querySelector(`[data-event-id="${id}"][data-event-type="${type}"]`);

    try {
        if (type === 'drop') {
            await DropsService.deleteDrop(id);
        } else {
            await StockService.deleteChange(id);
        }

        if (eventElement) {
            eventElement.style.opacity = '0';
            eventElement.style.transform = 'translateX(20px)';
            setTimeout(() => {
                eventElement.remove();
                checkEmptyDateGroups();
            }, 300);
        }

        showToast('Activity deleted successfully', 'success');
    } catch (error) {
        console.error('Failed to delete activity:', error);
        showToast('Failed to delete activity', 'error');
    }
}

function checkEmptyDateGroups() {
    const dateGroups = document.querySelectorAll('.activity-date-group');
    dateGroups.forEach(group => {
        const events = group.querySelector('.activity-events');
        if (events && events.children.length === 0) {
            group.remove();
        }
    });

    const timeline = document.getElementById('activity-timeline');
    if (timeline && timeline.children.length === 0) {
        timeline.innerHTML = `
            <div class="empty-state">
                <p class="empty-state-message">No activity found</p>
            </div>
        `;
    }
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
