/**
 * Centralized Date and Timezone Utilities
 * Handles timezone-aware datetime parsing and formatting
 */

const DateUtils = {
    /**
     * Parse various timestamp formats to Date object
     * Handles: ISO strings, Unix timestamps (seconds or milliseconds), Date objects
     *
     * @param {string|number|Date} value - Timestamp value
     * @returns {Date|null} Date object or null if invalid
     */
    parseTimestamp(value) {
        if (!value) return null;

        // Already a Date object
        if (value instanceof Date) {
            return value;
        }

        // Unix timestamp (number)
        if (typeof value === 'number') {
            // If less than 10000000000, it's in seconds (before year 2286)
            // Otherwise it's in milliseconds
            if (value < 10000000000) {
                return new Date(value * 1000);
            }
            return new Date(value);
        }

        // ISO string or other string format
        if (typeof value === 'string') {
            const date = new Date(value);
            return isNaN(date.getTime()) ? null : date;
        }

        return null;
    },

    /**
     * Format timestamp as "time ago" (e.g., "5m ago", "2h ago")
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @returns {string} Formatted time ago string
     */
    formatTimeAgo(timestamp) {
        const date = this.parseTimestamp(timestamp);
        if (!date) return 'Never';

        const now = new Date();
        const diffMs = now - date;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffDays > 0) return `${diffDays}d ago`;
        if (diffHours > 0) return `${diffHours}h ago`;
        if (diffMinutes > 0) return `${diffMinutes}m ago`;
        return 'Just now';
    },

    /**
     * Format timestamp as localized time string
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @param {object} options - Intl.DateTimeFormat options
     * @returns {string} Formatted time string
     */
    formatTime(timestamp, options = {}) {
        const date = this.parseTimestamp(timestamp);
        if (!date) return '--';

        const defaultOptions = {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
            timeZoneName: 'short'
        };

        try {
            return date.toLocaleTimeString('en-US', { ...defaultOptions, ...options });
        } catch (e) {
            console.error('Date formatting error:', e);
            return '--';
        }
    },

    /**
     * Format timestamp as localized date string
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @param {object} options - Intl.DateTimeFormat options
     * @returns {string} Formatted date string
     */
    formatDate(timestamp, options = {}) {
        const date = this.parseTimestamp(timestamp);
        if (!date) return '--';

        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        };

        try {
            return date.toLocaleDateString('en-US', { ...defaultOptions, ...options });
        } catch (e) {
            console.error('Date formatting error:', e);
            return '--';
        }
    },

    /**
     * Format timestamp as localized date and time string
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @param {object} options - Intl.DateTimeFormat options
     * @returns {string} Formatted datetime string
     */
    formatDateTime(timestamp, options = {}) {
        const date = this.parseTimestamp(timestamp);
        if (!date) return '--';

        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        };

        try {
            return date.toLocaleString('en-US', { ...defaultOptions, ...options });
        } catch (e) {
            console.error('Date formatting error:', e);
            return '--';
        }
    },

    /**
     * Format next window time intelligently
     * Shows relative time for near future, absolute time for far future
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @returns {string} Formatted next window string
     */
    formatNextWindow(timestamp) {
        const date = this.parseTimestamp(timestamp);
        if (!date) return '--';

        try {
            const now = new Date();
            const diffMs = date - now;
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffDays = Math.floor(diffHours / 24);

            if (diffHours < 1) {
                const diffMins = Math.floor(diffMs / (1000 * 60));
                return `${diffMins} min`;
            } else if (diffHours < 24) {
                return `${diffHours}h`;
            } else if (diffDays < 7) {
                const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
                const time = date.toLocaleTimeString('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                });
                return `${dayName} ${time}`;
            } else {
                return date.toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                });
            }
        } catch (e) {
            console.error('Date formatting error:', e);
            return '--';
        }
    },

    /**
     * Get timestamp as Unix seconds (for legacy compatibility)
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @returns {number} Unix timestamp in seconds
     */
    toUnixSeconds(timestamp) {
        const date = this.parseTimestamp(timestamp);
        return date ? Math.floor(date.getTime() / 1000) : 0;
    },

    /**
     * Get timestamp as Unix milliseconds
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @returns {number} Unix timestamp in milliseconds
     */
    toUnixMillis(timestamp) {
        const date = this.parseTimestamp(timestamp);
        return date ? date.getTime() : 0;
    },

    /**
     * Check if timestamp is valid
     *
     * @param {string|number|Date} timestamp - Timestamp value
     * @returns {boolean} True if valid timestamp
     */
    isValid(timestamp) {
        return this.parseTimestamp(timestamp) !== null;
    }
};

// Export globally for use throughout the app
window.DateUtils = DateUtils;

// Export individual functions for backwards compatibility
window.formatTimeAgo = (ts) => DateUtils.formatTimeAgo(ts);
window.formatTime = (ts, opts) => DateUtils.formatTime(ts, opts);
window.formatDate = (ts, opts) => DateUtils.formatDate(ts, opts);
window.formatDateTime = (ts, opts) => DateUtils.formatDateTime(ts, opts);
window.formatNextWindow = (ts) => DateUtils.formatNextWindow(ts);
