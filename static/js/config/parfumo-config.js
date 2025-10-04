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
            lastUpdateEl.textContent = data.last_full_update
                ? new Date(data.last_full_update).toLocaleString()
                : 'Never';
        }
        if (totalMappedEl) totalMappedEl.textContent = data.total_mapped || 0;
        if (withRatingsEl) withRatingsEl.textContent = data.total_with_ratings || 0;
        if (notFoundEl) notFoundEl.textContent = data.total_not_found || 0;

        if (data.currently_updating) {
            showParfumoProgress(data.update_progress || 0);
        } else {
            hideParfumoProgress();
        }
    } catch (error) {
        console.error('Error loading Parfumo status:', error);
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
            throw new Error(result.message || 'Failed to trigger update');
        }
    } catch (error) {
        console.error('Error triggering Parfumo update:', error);
        showAlert('Failed to trigger Parfumo update', 'error');
        if (statusEl) statusEl.textContent = 'Update failed';
    } finally {
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

let parfumoProgressInterval = null;

function pollParfumoProgress() {
    if (parfumoProgressInterval) {
        clearInterval(parfumoProgressInterval);
    }

    parfumoProgressInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/parfumo/status');
            if (!response.ok) return;

            const data = await response.json();

            if (data.currently_updating) {
                showParfumoProgress(data.update_progress || 0);
            } else {
                clearInterval(parfumoProgressInterval);
                parfumoProgressInterval = null;
                hideParfumoProgress();
                loadParfumoStatus();
                showAlert('Parfumo update completed', 'success');
            }
        } catch (error) {
            console.error('Error polling Parfumo status:', error);
        }
    }, 2000);
}

window.triggerParfumoUpdate = triggerParfumoUpdate;
