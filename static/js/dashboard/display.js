/**
 * Dashboard Display/Rendering Functions
 */

function displayRecentActivity(drops, stockChanges) {
    const container = document.getElementById('recent-activity-list');
    if (!container) return;

    const allActivity = [
        ...drops.map(drop => ({ ...drop, type: 'drop' })),
        ...stockChanges.map(change => ({ ...change, type: 'stock' }))
    ].sort((a, b) => {
        // Use DateUtils to parse timestamps properly
        const aTime = window.DateUtils.toUnixMillis(a.created_at || a.detected_at);
        const bTime = window.DateUtils.toUnixMillis(b.created_at || b.detected_at);
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
                            <span class="activity-time">${window.DateUtils.formatTimeAgo(item.created_at)}</span>
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
                            <span class="activity-time">${window.DateUtils.formatTimeAgo(item.detected_at)}</span>
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
