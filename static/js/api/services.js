/**
 * API Services
 * High-level service functions that use the API client
 */

const StatusService = {
    async getStatus() {
        return await apiClient.get(endpoints.status.get());
    },

    async getMonitorStatus() {
        return await apiClient.get(endpoints.status.monitor());
    }
};

const DropsService = {
    async getRecentDrops(limit = 10) {
        return await apiClient.get(endpoints.drops.list(limit));
    },

    async deleteDrop(dropId) {
        return await apiClient.delete(endpoints.drops.delete(dropId));
    }
};

const StockService = {
    async getRecentChanges(limit = 10) {
        return await apiClient.get(endpoints.stock.changes(limit));
    },

    async deleteChange(changeId) {
        return await apiClient.delete(endpoints.stock.deleteChange(changeId));
    },

    async getFragrances(params = {}) {
        return await apiClient.get(endpoints.stock.fragrances(params), {
            cache: !params.search, // Don't cache search results
            cacheTTL: 60000 // Cache for 1 minute
        });
    }
};

const WatchlistService = {
    async addItem(slug) {
        const result = await apiClient.post(endpoints.watchlist.add(slug));
        // Clear fragrance cache to reflect changes
        apiClient.clearCache('/api/stock/fragrances');
        return result;
    },

    async removeItem(slug) {
        const result = await apiClient.post(endpoints.watchlist.remove(slug));
        apiClient.clearCache('/api/stock/fragrances');
        return result;
    },

    async bulkAdd(slugs) {
        const result = await apiClient.post(endpoints.watchlist.bulkAdd(), { slugs });
        apiClient.clearCache('/api/stock/fragrances');
        return result;
    },

    async bulkRemove(slugs) {
        const result = await apiClient.delete(endpoints.watchlist.bulkRemove(), {
            body: { slugs }
        });
        apiClient.clearCache('/api/stock/fragrances');
        return result;
    }
};

const ConfigService = {
    async getConfig(forceFresh = false) {
        if (forceFresh) {
            apiClient.clearCache('/api/config');
        }
        return await apiClient.get(endpoints.config.get(), {
            cache: !forceFresh
        });
    },

    async saveRedditConfig(config) {
        const result = await apiClient.post(endpoints.config.reddit(), config);
        apiClient.clearCache('/api/config');
        return result;
    },

    async saveNotificationConfig(config) {
        const result = await apiClient.post(endpoints.config.notifications(), config);
        apiClient.clearCache('/api/config');
        return result;
    },

    async saveDetectionConfig(config) {
        const result = await apiClient.post(endpoints.config.detection(), config);
        apiClient.clearCache('/api/config');
        return result;
    },

    async saveDropWindowConfig(config) {
        const result = await apiClient.post(endpoints.config.dropWindow(), config);
        apiClient.clearCache('/api/config');
        return result;
    },

    async saveStockMonitoringConfig(config) {
        const result = await apiClient.post(endpoints.config.stockMonitoring(), config);
        apiClient.clearCache('/api/config');
        return result;
    },

    async saveStockScheduleConfig(config) {
        const result = await apiClient.post(endpoints.config.stockSchedule(), config);
        apiClient.clearCache('/api/config');
        return result;
    },

    async saveLoggingConfig(config) {
        const result = await apiClient.post(endpoints.config.logging(), config);
        apiClient.clearCache('/api/config');
        return result;
    }
};

const LogsService = {
    async getUsage() {
        return await apiClient.get(endpoints.logs.usage(), { cache: false });
    },

    async cleanup() {
        return await apiClient.post(endpoints.logs.cleanup());
    },

    downloadLogs() {
        // Direct download, no API client needed
        window.location.href = endpoints.logs.download();
    }
};

const TestService = {
    async testReddit(config) {
        return await apiClient.post(endpoints.test.reddit(), config);
    },

    async testNotifications() {
        return await apiClient.post(endpoints.test.notifications());
    },

    async testPushover() {
        return await apiClient.post(endpoints.test.pushover());
    },

    async testDiscord() {
        return await apiClient.post(endpoints.test.discord());
    },

    async testEmail() {
        return await apiClient.post(endpoints.test.email());
    },

    async testAll() {
        return await apiClient.post(endpoints.test.all());
    }
};

const ParfumoService = {
    async getStatus() {
        return await apiClient.get(endpoints.parfumo.status(), { cache: false });
    },

    async triggerUpdate() {
        return await apiClient.post(endpoints.parfumo.update());
    },

    async updateSingleFragrance(slug) {
        const result = await apiClient.post(endpoints.parfumo.updateSingle(slug));
        // Clear fragrance cache to reflect changes
        apiClient.clearCache('/api/stock/fragrances');
        return result;
    }
};

// Export all services
window.StatusService = StatusService;
window.DropsService = DropsService;
window.StockService = StockService;
window.WatchlistService = WatchlistService;
window.ConfigService = ConfigService;
window.LogsService = LogsService;
window.TestService = TestService;
window.ParfumoService = ParfumoService;
