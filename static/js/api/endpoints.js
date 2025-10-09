/**
 * API Endpoints Registry
 * Centralized definition of all API endpoints with typed parameters
 */

const endpoints = {
    // Health endpoints
    health: {
        check: () => '/health',
        ready: () => '/health/ready',
        live: () => '/health/live'
    },

    // Status endpoints
    status: {
        get: () => '/api/status',
        monitor: () => '/api/monitor/status'
    },

    // Drop endpoints
    drops: {
        list: (limit = 10) => `/api/drops?limit=${limit}`,
        delete: (id) => `/api/drops/${id}`
    },

    // Stock endpoints
    stock: {
        changes: (limit = 10) => `/api/stock/changes?limit=${limit}`,
        deleteChange: (id) => `/api/stock/changes/${id}`,
        fragrances: (params = {}) => {
            const query = new URLSearchParams();
            if (params.search) query.append('search', params.search);
            if (params.in_stock !== undefined) query.append('in_stock', params.in_stock);
            if (params.sort_by) query.append('sort_by', params.sort_by);
            if (params.sort_order) query.append('sort_order', params.sort_order);
            if (params.limit) query.append('limit', params.limit);
            if (params.offset) query.append('offset', params.offset);
            if (params.watchlist_only) query.append('watchlist_only', params.watchlist_only);
            if (params.include_ratings !== undefined) query.append('include_ratings', params.include_ratings);

            const queryString = query.toString();
            return `/api/stock/fragrances${queryString ? '?' + queryString : ''}`;
        }
    },

    // Watchlist endpoints
    watchlist: {
        add: (slug) => `/api/stock/watchlist/add/${slug}`,
        remove: (slug) => `/api/stock/watchlist/remove/${slug}`,
        bulkAdd: () => '/api/watchlist/bulk',
        bulkRemove: () => '/api/watchlist/bulk'
    },

    // Configuration endpoints
    config: {
        get: () => '/api/config',
        reddit: () => '/api/config/reddit',
        notifications: () => '/api/config/notifications',
        detection: () => '/api/config/detection',
        dropWindow: () => '/api/config/drop-window',
        stockMonitoring: () => '/api/config/stock-monitoring',
        stockSchedule: () => '/api/config/stock-schedule',
        parfumo: () => '/api/config/parfumo',
        logging: () => '/api/config/logging'
    },

    // Logging endpoints
    logs: {
        usage: () => '/api/logs/usage',
        cleanup: () => '/api/logs/cleanup',
        download: () => '/api/logs/download'
    },

    // Test endpoints
    test: {
        reddit: () => '/api/test/reddit',
        notifications: () => '/api/test/notifications',
        pushover: () => '/api/test/pushover',
        discord: () => '/api/test/discord',
        email: () => '/api/test/email',
        all: () => '/api/test/all'
    },

    // Parfumo endpoints
    parfumo: {
        status: () => '/api/parfumo/status',
        update: () => '/api/parfumo/update',
        updateSingle: (slug) => `/api/parfumo/update/${slug}`
    }
};

// Export for use in other modules
window.endpoints = endpoints;
