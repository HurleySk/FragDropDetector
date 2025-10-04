async function initializeConfiguration() {
    setupConfigurationTabs();
    bindConfigurationForms();
    await loadAllConfiguration();
    await updateRedditAuthStatus();
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

            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === `${targetTab}-tab`);
            });
        });
    });
}

async function loadAllConfiguration() {
    try {
        const config = await loadConfig(true);

        if (!config) {
            console.error('No configuration data received');
            return;
        }

        populateRedditConfig(config.reddit || {});
        populateNotificationConfig(config.notifications || {});
        populateDetectionConfig(config.detection || {});
        populateDropWindowConfig(config.drop_window || {});
        populateStockMonitoringConfig(config.stock_monitoring || {});
        populateStockScheduleConfig(config.stock_schedule || {});
        populateParfumoConfig(config.parfumo || {});
        populateLoggingConfig(config.logging || {});

        refreshLogUsage();
        loadParfumoStatus();
    } catch (error) {
        console.error('Failed to load configuration:', error);
        showAlert('Failed to load configuration', 'error');
    }
}

function bindConfigurationForms() {
    const redditForm = document.getElementById('reddit-form');
    if (redditForm) {
        redditForm.addEventListener('submit', handleRedditConfigSubmit);
    }

    const detectionForm = document.getElementById('detection-form');
    if (detectionForm) {
        detectionForm.addEventListener('submit', handleDetectionConfigSubmit);
    }

    const stockForm = document.getElementById('stock-form');
    if (stockForm) {
        stockForm.addEventListener('submit', handleStockConfigSubmit);
    }

    const stockScheduleForm = document.getElementById('stock-schedule-form');
    if (stockScheduleForm) {
        stockScheduleForm.addEventListener('submit', handleStockScheduleConfigSubmit);
    }

    const parfumoForm = document.getElementById('parfumo-form');
    if (parfumoForm) {
        parfumoForm.addEventListener('submit', handleParfumoConfigSubmit);
    }

    const loggingForm = document.getElementById('logging-form');
    if (loggingForm) {
        loggingForm.addEventListener('submit', saveLoggingConfig);
    }

    const redditWindowToggle = document.getElementById('window-enabled');
    const redditWindowConfig = document.getElementById('reddit-window-config');
    if (redditWindowToggle && redditWindowConfig) {
        redditWindowToggle.addEventListener('change', () => {
            redditWindowConfig.style.display = redditWindowToggle.checked ? 'block' : 'none';
        });
    }

    const stockWindowToggle = document.getElementById('stock-window-enabled');
    const stockWindowConfig = document.getElementById('stock-window-config');
    if (stockWindowToggle && stockWindowConfig) {
        stockWindowToggle.addEventListener('change', () => {
            stockWindowConfig.style.display = stockWindowToggle.checked ? 'block' : 'none';
        });
    }

    const thresholdSlider = document.getElementById('confidence-threshold');
    if (thresholdSlider) {
        thresholdSlider.addEventListener('input', (e) => {
            document.getElementById('confidence-value').textContent = e.target.value;
        });
    }

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
