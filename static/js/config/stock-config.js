function populateStockMonitoringConfig(config) {
    const stockConfig = config || {};
    const notifications = stockConfig.notifications || {};

    const stockEnabledEl = document.getElementById('stock-enabled');
    const newProductsEl = document.getElementById('notify-new-products');
    const restockedEl = document.getElementById('notify-restocked');
    const priceChangesEl = document.getElementById('notify-price-changes');
    const outOfStockEl = document.getElementById('notify-out-of-stock');

    if (stockEnabledEl) stockEnabledEl.checked = stockConfig.enabled !== false;
    if (newProductsEl) newProductsEl.checked = notifications.new_products !== false;
    if (restockedEl) restockedEl.checked = notifications.restocked_products !== false;
    if (priceChangesEl) priceChangesEl.checked = notifications.price_changes === true;
    if (outOfStockEl) outOfStockEl.checked = notifications.out_of_stock === true;
}

function populateStockScheduleConfig(config) {
    const scheduleConfig = config || {};

    const scheduleEnabledEl = document.getElementById('stock-schedule-enabled');
    const checkIntervalEl = document.getElementById('stock-check-interval');
    const windowEnabledEl = document.getElementById('stock-window-enabled');
    const windowConfigEl = document.getElementById('stock-window-config');

    if (scheduleEnabledEl) scheduleEnabledEl.checked = scheduleConfig.enabled !== false;
    if (checkIntervalEl) checkIntervalEl.value = scheduleConfig.check_interval || 1800;
    if (windowEnabledEl) {
        windowEnabledEl.checked = scheduleConfig.window_enabled === true;
        if (windowConfigEl) {
            windowConfigEl.style.display = scheduleConfig.window_enabled ? 'block' : 'none';
        }
    }

    const timezoneEl = document.getElementById('stock-window-timezone');
    const startTimeEl = document.getElementById('stock-window-start-time');
    const endTimeEl = document.getElementById('stock-window-end-time');

    if (timezoneEl) timezoneEl.value = scheduleConfig.timezone || 'America/New_York';

    const startTime = `${String(scheduleConfig.start_hour || 9).padStart(2, '0')}:${String(scheduleConfig.start_minute || 0).padStart(2, '0')}`;
    const endTime = `${String(scheduleConfig.end_hour || 18).padStart(2, '0')}:${String(scheduleConfig.end_minute || 0).padStart(2, '0')}`;

    if (startTimeEl) startTimeEl.value = startTime;
    if (endTimeEl) endTimeEl.value = endTime;

    const activeDays = scheduleConfig.days_of_week || [];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`stock-day-${i}`);
        if (checkbox) {
            checkbox.checked = activeDays.includes(i);
        }
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
        const refreshedConfig = await loadConfig(true);
        if (refreshedConfig) {
            populateStockMonitoringConfig(refreshedConfig.stock_monitoring || {});
        }
    } catch (error) {
        // Error already shown
    } finally {
        setLoading('stock-form', false);
    }
}

async function handleStockScheduleConfigSubmit(e) {
    e.preventDefault();

    const windowEnabled = document.getElementById('stock-window-enabled').checked;
    const startTime = document.getElementById('stock-window-start-time').value.split(':');
    const endTime = document.getElementById('stock-window-end-time').value.split(':');

    const days = [];
    for (let i = 0; i <= 6; i++) {
        const checkbox = document.getElementById(`stock-day-${i}`);
        if (checkbox && checkbox.checked) {
            days.push(i);
        }
    }

    const config = {
        enabled: document.getElementById('stock-schedule-enabled').checked,
        check_interval: parseInt(document.getElementById('stock-check-interval').value),
        window_enabled: windowEnabled,
        timezone: document.getElementById('stock-window-timezone').value,
        days_of_week: days,
        start_hour: parseInt(startTime[0]),
        start_minute: parseInt(startTime[1]),
        end_hour: parseInt(endTime[0]),
        end_minute: parseInt(endTime[1])
    };

    try {
        setLoading('stock-schedule-form', true);
        await saveStockScheduleConfig(config);
        const refreshedConfig = await loadConfig(true);
        if (refreshedConfig) {
            populateStockScheduleConfig(refreshedConfig.stock_schedule || {});
        }
    } catch (error) {
        // Error already shown
    } finally {
        setLoading('stock-schedule-form', false);
    }
}
