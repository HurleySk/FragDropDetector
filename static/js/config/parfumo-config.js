function populateParfumoConfig(config) {
    const enabledEl = document.getElementById('parfumo-enabled');
    const timeEl = document.getElementById('parfumo-update-time');
    const autoScrapeEl = document.getElementById('parfumo-auto-scrape');

    if (enabledEl) enabledEl.checked = config.enabled !== false;
    if (timeEl) timeEl.value = config.update_time || '02:00';
    if (autoScrapeEl) autoScrapeEl.checked = config.auto_scrape_new !== false;
}

async function handleParfumoConfigSubmit(e) {
    e.preventDefault();

    const config = {
        enabled: document.getElementById('parfumo-enabled').checked,
        update_time: document.getElementById('parfumo-update-time').value || '02:00',
        auto_scrape_new: document.getElementById('parfumo-auto-scrape').checked
    };

    try {
        const response = await fetch('/api/config/parfumo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showAlert('Parfumo settings saved successfully', 'success');
        } else {
            throw new Error(result.detail || 'Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving Parfumo config:', error);
        showAlert('Failed to save Parfumo settings', 'error');
    }
}

async function loadParfumoStatus() {
    try {
        const response = await fetch('/api/parfumo/status');
        if (!response.ok) return;

        const data = await response.json();

        const lastUpdateEl = document.getElementById('parfumo-last-update');
        const totalMappedEl = document.getElementById('parfumo-total-mapped');
        const withRatingsEl = document.getElementById('parfumo-with-ratings');
        const notFoundEl = document.getElementById('parfumo-not-found');

        if (lastUpdateEl) {
            if (data.last_full_update) {
                const timezone = data.timezone || 'America/New_York';
                lastUpdateEl.textContent = new Date(data.last_full_update).toLocaleString('en-US', {
                    timeZone: timezone,
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                });
            } else {
                lastUpdateEl.textContent = 'Never';
            }
        }
        if (totalMappedEl) totalMappedEl.textContent = data.total_mapped || 0;
        if (withRatingsEl) withRatingsEl.textContent = data.total_with_ratings || 0;
        if (notFoundEl) notFoundEl.textContent = data.total_not_found || 0;

        updateFragscrapeStatus(data.fragscrape_available, data.fragscrape_url);

        // If update is in progress, show progress and start polling
        if (data.currently_updating) {
            showParfumoProgress(data.update_progress || 0);
            // Start polling if not already polling
            if (!window.parfumoProgressInterval) {
                pollParfumoProgress();
            }
        } else {
            hideParfumoProgress();
            // Start periodic refresh when not updating
            startPeriodicRefresh();
        }

        // Load unmatched fragrances list
        loadUnmatchedFragrances();
    } catch (error) {
        console.error('Error loading Parfumo status:', error);
    }
}

function startPeriodicRefresh() {
    // Clear any existing periodic refresh
    if (window.parfumoPeriodicRefresh) {
        clearInterval(window.parfumoPeriodicRefresh);
    }

    // Refresh stats every 30 seconds when on Parfumo tab
    window.parfumoPeriodicRefresh = setInterval(async () => {
        // Only refresh if we're on the Parfumo tab and not actively updating
        const parfumoTab = document.getElementById('parfumo-tab');
        if (parfumoTab && parfumoTab.style.display !== 'none' && !window.parfumoProgressInterval) {
            try {
                const response = await fetch('/api/parfumo/status');
                if (response.ok) {
                    const data = await response.json();
                    updateParfumoStats(data);

                    // If an update started, switch to active polling
                    if (data.currently_updating) {
                        clearInterval(window.parfumoPeriodicRefresh);
                        window.parfumoPeriodicRefresh = null;
                        pollParfumoProgress();
                    }
                }
            } catch (error) {
                console.error('Error in periodic refresh:', error);
            }
        }
    }, 30000); // 30 seconds
}

function updateFragscrapeStatus(available, url) {
    const updateBtn = document.getElementById('parfumo-update-btn');
    let warningEl = document.getElementById('fragscrape-warning');

    if (!available) {
        if (updateBtn) {
            updateBtn.disabled = true;
            updateBtn.title = 'fragscrape API not available';
        }

        if (!warningEl) {
            warningEl = document.createElement('div');
            warningEl.id = 'fragscrape-warning';
            warningEl.className = 'warning-banner';
            warningEl.innerHTML = `
                <div class="warning-content">
                    <strong>fragscrape API not detected</strong>
                    <p>The Parfumo integration requires fragscrape to be running.</p>
                    <p>Install from: <a href="https://github.com/HurleySk/fragscrape" target="_blank">https://github.com/HurleySk/fragscrape</a></p>
                    ${url ? `<p>Expected URL: <code>${url}</code></p>` : ''}
                </div>
            `;

            const parfumoTab = document.getElementById('parfumo-tab');
            if (parfumoTab) {
                parfumoTab.insertBefore(warningEl, parfumoTab.firstChild);
            }
        }
    } else {
        if (updateBtn) {
            updateBtn.disabled = false;
            updateBtn.title = 'Trigger manual Parfumo update';
        }

        if (warningEl) {
            warningEl.remove();
        }
    }
}

async function triggerParfumoUpdate() {
    const updateBtn = document.getElementById('parfumo-update-btn');
    const statusEl = document.getElementById('parfumo-update-status');

    if (updateBtn) updateBtn.disabled = true;
    if (statusEl) statusEl.textContent = 'Starting update...';

    try {
        const response = await fetch('/api/parfumo/update', {
            method: 'POST'
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showAlert(result.message, 'success');
            if (statusEl) statusEl.textContent = 'Update started';

            pollParfumoProgress();
        } else {
            const errorMsg = result.message || 'Failed to trigger update';
            showAlert(errorMsg, 'error');
            if (statusEl) statusEl.textContent = 'Update failed';
            if (updateBtn) updateBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error triggering Parfumo update:', error);
        showAlert('Failed to trigger Parfumo update', 'error');
        if (statusEl) statusEl.textContent = 'Update failed';
        if (updateBtn) updateBtn.disabled = false;
    }
}

function showParfumoProgress(progress) {
    const progressDiv = document.getElementById('parfumo-progress');
    const progressBar = document.getElementById('parfumo-progress-bar');
    const progressText = document.getElementById('parfumo-progress-text');

    if (progressDiv) progressDiv.style.display = 'block';
    if (progressBar) progressBar.style.width = `${progress}%`;
    if (progressText) progressText.textContent = `Updating... ${progress}%`;
}

function hideParfumoProgress() {
    const progressDiv = document.getElementById('parfumo-progress');
    if (progressDiv) progressDiv.style.display = 'none';
}

function pollParfumoProgress() {
    // Use global interval so it persists across page navigation
    if (window.parfumoProgressInterval) {
        clearInterval(window.parfumoProgressInterval);
    }

    window.parfumoProgressInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/parfumo/status');
            if (!response.ok) return;

            const data = await response.json();

            if (data.currently_updating) {
                showParfumoProgress(data.update_progress || 0);

                // Update stats dynamically during update
                updateParfumoStats(data);
            } else {
                clearInterval(window.parfumoProgressInterval);
                window.parfumoProgressInterval = null;
                hideParfumoProgress();
                loadParfumoStatus();
                showAlert('Parfumo update completed', 'success');
            }
        } catch (error) {
            console.error('Error polling Parfumo status:', error);
        }
    }, 2000);
}

function updateParfumoStats(data) {
    const totalMappedEl = document.getElementById('parfumo-total-mapped');
    const withRatingsEl = document.getElementById('parfumo-with-ratings');
    const notFoundEl = document.getElementById('parfumo-not-found');

    if (totalMappedEl) totalMappedEl.textContent = data.total_mapped || 0;
    if (withRatingsEl) withRatingsEl.textContent = data.total_with_ratings || 0;
    if (notFoundEl) notFoundEl.textContent = data.total_not_found || 0;
}

async function loadUnmatchedFragrances() {
    try {
        const response = await fetch('/api/parfumo/unmatched');
        if (!response.ok) return;

        const data = await response.json();

        const card = document.getElementById('unmatched-fragrances-card');
        const countBadge = document.getElementById('unmatched-count');
        const listEl = document.getElementById('unmatched-list');

        if (data.count === 0) {
            // Hide card if no unmatched fragrances
            if (card) card.style.display = 'none';
            return;
        }

        // Show card and update count
        if (card) card.style.display = 'block';
        if (countBadge) countBadge.textContent = `(${data.count})`;

        // Render list
        if (listEl) {
            listEl.innerHTML = data.fragrances.map(frag => `
                <div class="unmatched-item" data-slug="${frag.slug}">
                    <div class="fragrance-info">
                        <strong>${frag.name}</strong>
                        <small>Original: ${frag.original_brand} - ${frag.original_name}</small>
                    </div>
                    <div class="url-input-group">
                        <input
                            type="url"
                            placeholder="https://www.parfumo.com/..."
                            class="form-input parfumo-url-input"
                            data-slug="${frag.slug}"
                        >
                        <button
                            class="btn-icon search-btn"
                            title="Search Parfumo"
                            onclick="searchParfumoFor('${frag.original_brand.replace(/'/g, "\\'")}', '${frag.original_name.replace(/'/g, "\\'")}')"
                        >
                            🔍
                        </button>
                        <button
                            class="btn-icon save-btn success"
                            title="Save URL"
                            onclick="saveParfumoUrl('${frag.slug}')"
                        >
                            ✓
                        </button>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading unmatched fragrances:', error);
    }
}

function searchParfumoFor(brand, name) {
    // Parfumo uses this search format: s_perfumes_x.php?in=1&order=&filter=query
    const query = encodeURIComponent(`${brand} ${name}`);
    const url = `https://www.parfumo.com/s_perfumes_x.php?in=1&order=&filter=${query}`;
    window.open(url, '_blank');
}

async function saveParfumoUrl(slug) {
    const input = document.querySelector(`.parfumo-url-input[data-slug="${slug}"]`);
    if (!input) return;

    const parfumoUrl = input.value.trim();

    if (!parfumoUrl) {
        showAlert('Please enter a Parfumo URL', 'error');
        return;
    }

    if (!parfumoUrl.startsWith('https://www.parfumo.com/')) {
        showAlert('Invalid Parfumo URL. Must start with https://www.parfumo.com/', 'error');
        return;
    }

    // Disable button during save
    const saveBtn = input.parentElement.querySelector('.save-btn');
    if (saveBtn) saveBtn.disabled = true;

    try {
        const response = await fetch('/api/parfumo/manual-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ slug, parfumo_url: parfumoUrl })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showAlert(result.message, 'success');

            // Remove this item from the list
            const item = document.querySelector(`.unmatched-item[data-slug="${slug}"]`);
            if (item) item.remove();

            // Reload stats and unmatched list
            loadParfumoStatus();
            loadUnmatchedFragrances();
        } else {
            showAlert(result.message || 'Failed to save Parfumo URL', 'error');
            if (saveBtn) saveBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error saving Parfumo URL:', error);
        showAlert('Failed to save Parfumo URL', 'error');
        if (saveBtn) saveBtn.disabled = false;
    }
}

window.triggerParfumoUpdate = triggerParfumoUpdate;
window.searchParfumoFor = searchParfumoFor;
window.saveParfumoUrl = saveParfumoUrl;
window.loadUnmatchedFragrances = loadUnmatchedFragrances;
