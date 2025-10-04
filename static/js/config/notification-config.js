function populateNotificationConfig(config) {
    const pushoverToken = config.pushover_app_token || '';
    const pushoverKey = config.pushover_user_key || '';
    const discordWebhook = config.discord_webhook_url || '';

    const pushoverTokenEl = document.getElementById('pushover-app-token');
    const pushoverKeyEl = document.getElementById('pushover-user-key');
    const discordWebhookEl = document.getElementById('discord-webhook');

    if (pushoverTokenEl) pushoverTokenEl.value = pushoverToken;
    if (pushoverKeyEl) pushoverKeyEl.value = pushoverKey;
    if (discordWebhookEl) discordWebhookEl.value = discordWebhook;

    updateNotificationStatus('pushover', pushoverToken.length > 0 && pushoverKey.length > 0);
    updateNotificationStatus('discord', discordWebhook.length > 0);
}

function updateNotificationStatus(service, enabled) {
    const statusElement = document.getElementById(`${service}-status`);
    const indicator = statusElement?.querySelector('.status-indicator');
    const text = statusElement?.querySelector('.status-text');

    if (indicator) {
        indicator.className = `status-indicator ${enabled ? 'enabled' : 'disabled'}`;
    }

    if (text) {
        text.textContent = enabled ? 'Configured' : 'Not configured';
    }
}

function updateNotificationStatuses() {
    const pushoverToken = document.getElementById('pushover-app-token').value;
    const pushoverUser = document.getElementById('pushover-user-key').value;
    const discordWebhook = document.getElementById('discord-webhook').value;

    updateNotificationStatus('pushover', pushoverToken.length > 0 && pushoverUser.length > 0);
    updateNotificationStatus('discord', discordWebhook.length > 0);
}

async function handleNotificationConfigSubmit() {
    const config = {
        pushover_app_token: document.getElementById('pushover-app-token').value || null,
        pushover_user_key: document.getElementById('pushover-user-key').value || null,
        discord_webhook_url: document.getElementById('discord-webhook').value || null
    };

    try {
        setLoading('notifications-tab', true);
        await saveNotificationConfig(config);
        const refreshedConfig = await loadConfig(true);
        if (refreshedConfig) {
            populateNotificationConfig(refreshedConfig.notifications || {});
        }
    } catch (error) {
        // Error already shown
    } finally {
        setLoading('notifications-tab', false);
    }
}
