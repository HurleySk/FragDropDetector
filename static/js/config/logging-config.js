function populateLoggingConfig(config) {
    document.getElementById('file-logging-enabled').checked = config.file_enabled !== false;
    document.getElementById('log-level').value = config.level || 'INFO';
    document.getElementById('max-file-size').value = config.max_file_size || 10;
    document.getElementById('backup-count').value = config.backup_count || 5;

    const autoCleanup = config.auto_cleanup || {};
    document.getElementById('auto-cleanup-enabled').checked = autoCleanup.enabled !== false;
    document.getElementById('max-age-days').value = autoCleanup.max_age_days || 30;
    document.getElementById('max-total-size').value = autoCleanup.max_total_size_mb || 100;
    document.getElementById('cleanup-interval').value = autoCleanup.cleanup_interval_hours || 24;
    document.getElementById('cache-max-age').value = autoCleanup.cache_max_age_days || 7;
    document.getElementById('compress-old-logs').checked = autoCleanup.compress_old_logs !== false;
    document.getElementById('clean-cache').checked = autoCleanup.clean_cache !== false;
}

async function saveLoggingConfig(event) {
    event.preventDefault();

    const config = {
        level: document.getElementById('log-level').value,
        file_enabled: document.getElementById('file-logging-enabled').checked,
        file_path: 'logs/fragdrop.log',
        max_file_size: parseInt(document.getElementById('max-file-size').value),
        backup_count: parseInt(document.getElementById('backup-count').value),
        auto_cleanup: {
            enabled: document.getElementById('auto-cleanup-enabled').checked,
            max_age_days: parseInt(document.getElementById('max-age-days').value),
            max_total_size_mb: parseInt(document.getElementById('max-total-size').value),
            cleanup_interval_hours: parseInt(document.getElementById('cleanup-interval').value),
            compress_old_logs: document.getElementById('compress-old-logs').checked,
            clean_cache: document.getElementById('clean-cache').checked,
            cache_max_age_days: parseInt(document.getElementById('cache-max-age').value)
        }
    };

    try {
        const response = await fetch('/api/config/logging', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            showAlert('Logging configuration saved successfully', 'success');
            const refreshedConfig = await loadConfig(true);
            if (refreshedConfig) {
                populateLoggingConfig(refreshedConfig.logging || {});
            }
        } else {
            showAlert('Failed to save logging configuration', 'error');
        }
    } catch (error) {
        console.error('Error saving logging config:', error);
        showAlert('Failed to save logging configuration', 'error');
    }
}

async function refreshLogUsage() {
    try {
        const response = await fetch('/api/logs/usage');
        const usage = await response.json();

        document.getElementById('total-log-size').textContent = `${usage.total_mb.toFixed(2)} MB`;
        document.getElementById('logs-dir-size').textContent = `${usage.logs_dir_mb.toFixed(2)} MB`;
        document.getElementById('cache-dir-size').textContent = `${usage.cache_dir_mb.toFixed(2)} MB`;
        document.getElementById('log-file-count').textContent = usage.file_count;

        if (usage.oldest_file) {
            const date = new Date(usage.oldest_file.date);
            document.getElementById('oldest-log-file').textContent =
                `${usage.oldest_file.name} (${date.toLocaleDateString()})`;
        } else {
            document.getElementById('oldest-log-file').textContent = 'N/A';
        }
    } catch (error) {
        console.error('Error fetching log usage:', error);
    }
}

async function manualCleanup() {
    if (!confirm('This will delete old log files according to your cleanup settings. Continue?')) {
        return;
    }

    try {
        const response = await fetch('/api/logs/cleanup', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showAlert(data.message, 'success');
            await refreshLogUsage();
        } else {
            showAlert('Cleanup failed', 'error');
        }
    } catch (error) {
        console.error('Error during cleanup:', error);
        showAlert('Failed to run cleanup', 'error');
    }
}

async function downloadLogs() {
    try {
        const link = document.createElement('a');
        link.href = '/api/logs/download';
        link.download = `logs_backup_${new Date().toISOString().split('T')[0]}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showAlert('Preparing logs download...', 'success');
    } catch (error) {
        console.error('Error downloading logs:', error);
        showAlert('Failed to download logs', 'error');
    }
}

window.refreshLogUsage = refreshLogUsage;
window.manualCleanup = manualCleanup;
window.downloadLogs = downloadLogs;
