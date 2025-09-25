// Configuration page functionality

async function initializeConfiguration() {
    setupConfigurationTabs();
    bindConfigurationForms();
    // Ensure configuration loads after DOM is ready
    await loadAllConfiguration();
}

function cleanupConfiguration() {
    // No specific cleanup needed for configuration page
}

function setupConfigurationTabs() {
    const tabButtons = document.querySelectorAll('.config-tabs .tab-btn');
    const tabContents = document.querySelectorAll('.config-tabs .tab-content');

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
        });
    });
}

async function loadAllConfiguration() {
    try {
        // Always fetch fresh config when loading the configuration page
        const config = await loadConfig();

        if (!config) {
            console.error('No configuration data received');
            return;
        }

        populateRedditConfig(config.reddit || {});
        populateNotificationConfig(config.notifications || {});
        populateDetectionConfig(config.detection || {});
        populateDropWindowConfig(config.drop_window || {});
        populateStockMonitoringConfig(config.stock_monitoring || {});
    } catch (error) {
        console.error('Failed to load configuration:', error);
        showAlert('Failed to load configuration', 'error');
    }
}

function populateRedditConfig(config) {
    const clientIdEl = document.getElementById('reddit-client-id');
    const clientSecretEl = document.getElementById('reddit-client-secret');
    const subredditEl = document.getElementById('reddit-subreddit');
    const intervalEl = document.getElementById('reddit-interval');

    if (clientIdEl) clientIdEl.value = config.client_id || '';
    if (clientSecretEl) clientSecretEl.value = config.client_secret || '';
    if (subredditEl) subredditEl.value = config.subreddit || 'MontagneParfums';
    if (intervalEl) intervalEl.value = config.check_interval || 300;
}

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

    // Update status indicators - check for non-empty strings
    updateNotificationStatus('pushover', pushoverToken.length > 0 && pushoverKey.length > 0);
    updateNotificationStatus('discord', discordWebhook.length > 0);
}

function populateDetectionConfig(config) {
    const primaryKeywords = config.primary_keywords || ['drop', 'dropped', 'release', 'available', 'launch'];
    const secondaryKeywords = config.secondary_keywords || ['limited', 'exclusive', 'sale', 'batch', 'decant'];

    document.getElementById('primary-keywords').value = primaryKeywords.join('\n');
    document.getElementById('secondary-keywords').value = secondaryKeywords.join('\n');

    const threshold = config.confidence_threshold || 0.4;
    document.getElementById('confidence-threshold').value = threshold;
    document.getElementById('confidence-value').textContent = threshold;
}

function populateDropWindowConfig(config) {
    document.getElementById('window-enabled').value = String(config.enabled !== false);
    document.getElementById('window-timezone').value = config.timezone || 'America/New_York';

    const startTime = `${String(config.start_hour || 12).padStart(2, '0')}:${String(config.start_minute || 0).padStart(2, '0')}`;
    const endTime = `${String(config.end_hour || 17).padStart(2, '0')}:${String(config.end_minute || 0).padStart(2, '0')}`;

    document.getElementById('window-start-time').value = startTime;
    document.getElementById('window-end-time').value = endTime;

    // Set active days
    const activeDays = config.days_of_week || [4];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`day-${i}`);
        if (checkbox) {
            checkbox.checked = activeDays.includes(i);
        }
    }
}

function populateStockMonitoringConfig(config) {
    const stockConfig = config || {};
    const notifications = stockConfig.notifications || {};

    document.getElementById('stock-enabled').checked = stockConfig.enabled !== false;
    document.getElementById('notify-new-products').checked = notifications.new_products !== false;
    document.getElementById('notify-restocked').checked = notifications.restocked_products !== false;
    document.getElementById('notify-price-changes').checked = notifications.price_changes === true;
    document.getElementById('notify-out-of-stock').checked = notifications.out_of_stock === true;
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

function bindConfigurationForms() {
    // Reddit form
    const redditForm = document.getElementById('reddit-form');
    if (redditForm) {
        redditForm.addEventListener('submit', handleRedditConfigSubmit);
    }

    // Detection form
    const detectionForm = document.getElementById('detection-form');
    if (detectionForm) {
        detectionForm.addEventListener('submit', handleDetectionConfigSubmit);
    }

    // Window form
    const windowForm = document.getElementById('window-form');
    if (windowForm) {
        windowForm.addEventListener('submit', handleWindowConfigSubmit);
    }

    // Stock form
    const stockForm = document.getElementById('stock-form');
    if (stockForm) {
        stockForm.addEventListener('submit', handleStockConfigSubmit);
    }

    // Confidence threshold slider
    const thresholdSlider = document.getElementById('confidence-threshold');
    if (thresholdSlider) {
        thresholdSlider.addEventListener('input', (e) => {
            document.getElementById('confidence-value').textContent = e.target.value;
        });
    }

    // Notification inputs (for real-time status updates)
    const notificationInputs = [
        'pushover-app-token', 'pushover-user-key', 'discord-webhook'
    ];

    notificationInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('input', updateNotificationStatuses);
        }
    });
}

function updateNotificationStatuses() {
    const pushoverToken = document.getElementById('pushover-app-token').value;
    const pushoverUser = document.getElementById('pushover-user-key').value;
    const discordWebhook = document.getElementById('discord-webhook').value;

    updateNotificationStatus('pushover', pushoverToken.length > 0 && pushoverUser.length > 0);
    updateNotificationStatus('discord', discordWebhook.length > 0);
}

async function handleRedditConfigSubmit(e) {
    e.preventDefault();

    const config = {
        client_id: document.getElementById('reddit-client-id').value,
        client_secret: document.getElementById('reddit-client-secret').value,
        user_agent: 'FragDropDetector/1.0',
        subreddit: document.getElementById('reddit-subreddit').value,
        check_interval: parseInt(document.getElementById('reddit-interval').value),
        post_limit: 50
    };

    if (!config.client_id || !config.client_secret) {
        showAlert('Please fill in all required Reddit credentials', 'error');
        return;
    }

    try {
        setLoading('reddit-form', true);
        await saveRedditConfig(config);
    } catch (error) {
        // Error already shown in saveRedditConfig
    } finally {
        setLoading('reddit-form', false);
    }
}

async function handleDetectionConfigSubmit(e) {
    e.preventDefault();

    const primaryKeywords = document.getElementById('primary-keywords').value
        .split('\n')
        .map(k => k.trim())
        .filter(k => k);

    const secondaryKeywords = document.getElementById('secondary-keywords').value
        .split('\n')
        .map(k => k.trim())
        .filter(k => k);

    const config = {
        primary_keywords: primaryKeywords,
        secondary_keywords: secondaryKeywords,
        confidence_threshold: parseFloat(document.getElementById('confidence-threshold').value),
        known_vendors: ['montagneparfums', 'montagne_parfums']
    };

    if (primaryKeywords.length === 0) {
        showAlert('Please add at least one primary keyword', 'error');
        return;
    }

    try {
        setLoading('detection-form', true);
        await saveDetectionConfig(config);
    } catch (error) {
        // Error already shown in saveDetectionConfig
    } finally {
        setLoading('detection-form', false);
    }
}

async function handleWindowConfigSubmit(e) {
    e.preventDefault();

    const enabled = document.getElementById('window-enabled').value === 'true';
    const timezone = document.getElementById('window-timezone').value;
    const startTime = document.getElementById('window-start-time').value.split(':');
    const endTime = document.getElementById('window-end-time').value.split(':');

    // Get selected days
    const days = [];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`day-${i}`);
        if (checkbox && checkbox.checked) {
            days.push(i);
        }
    }

    const config = {
        enabled,
        timezone,
        days_of_week: days,
        start_hour: parseInt(startTime[0]),
        start_minute: parseInt(startTime[1]),
        end_hour: parseInt(endTime[0]),
        end_minute: parseInt(endTime[1])
    };

    if (enabled && days.length === 0) {
        showAlert('Please select at least one day when window checking is enabled', 'error');
        return;
    }

    try {
        setLoading('window-form', true);
        await saveDropWindowConfig(config);
    } catch (error) {
        // Error already shown in saveDropWindowConfig
    } finally {
        setLoading('window-form', false);
    }
}

async function handleStockConfigSubmit(e) {
    e.preventDefault();

    const config = {
        enabled: document.getElementById('stock-enabled').checked,
        new_products: document.getElementById('notify-new-products').checked,
        restocked_products: document.getElementById('notify-restocked').checked,
        price_changes: document.getElementById('notify-price-changes').checked,
        out_of_stock: document.getElementById('notify-out-of-stock').checked
    };

    try {
        setLoading('stock-form', true);
        await saveStockMonitoringConfig(config);
    } catch (error) {
        // Error already shown in saveStockMonitoringConfig
    } finally {
        setLoading('stock-form', false);
    }
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
    } catch (error) {
        // Error already shown in saveNotificationConfig
    } finally {
        setLoading('notifications-tab', false);
    }
}