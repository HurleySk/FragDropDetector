/**
 * Centralized API Client
 * Handles all HTTP communication with consistent error handling, caching, and retries
 */

class ApiError extends Error {
    constructor(message, status, detail) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.detail = detail;
    }
}

class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.cache = new Map();
        this.defaultCacheTTL = 30000; // 30 seconds
    }

    /**
     * Make a GET request with caching support
     */
    async get(endpoint, options = {}) {
        const {
            cache = true,
            cacheTTL = this.defaultCacheTTL,
            ...fetchOptions
        } = options;

        const cacheKey = this._getCacheKey('GET', endpoint);

        if (cache) {
            const cached = this._getFromCache(cacheKey);
            if (cached) {
                return cached;
            }
        }

        const data = await this._request('GET', endpoint, null, fetchOptions);

        if (cache) {
            this._setCache(cacheKey, data, cacheTTL);
        }

        return data;
    }

    /**
     * Make a POST request
     */
    async post(endpoint, body = null, options = {}) {
        return this._request('POST', endpoint, body, options);
    }

    /**
     * Make a PUT request
     */
    async put(endpoint, body = null, options = {}) {
        return this._request('PUT', endpoint, body, options);
    }

    /**
     * Make a DELETE request
     */
    async delete(endpoint, options = {}) {
        return this._request('DELETE', endpoint, null, options);
    }

    /**
     * Core request method with error handling and retries
     */
    async _request(method, endpoint, body = null, options = {}) {
        const {
            retries = 0,
            retryDelay = 1000,
            headers = {},
            ...fetchOptions
        } = options;

        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...headers
            },
            ...fetchOptions
        };

        if (body !== null) {
            config.body = JSON.stringify(body);
        }

        let lastError;
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const response = await fetch(url, config);

                if (!response.ok) {
                    const error = await response.json().catch(() => ({
                        detail: `HTTP ${response.status}: ${response.statusText}`
                    }));
                    throw new ApiError(
                        error.detail || `Request failed with status ${response.status}`,
                        response.status,
                        error
                    );
                }

                return await response.json();
            } catch (error) {
                lastError = error;

                if (attempt < retries) {
                    await this._delay(retryDelay * Math.pow(2, attempt));
                }
            }
        }

        throw lastError;
    }

    /**
     * Clear all cached data
     */
    clearCache(pattern = null) {
        if (pattern) {
            for (const [key] of this.cache) {
                if (key.includes(pattern)) {
                    this.cache.delete(key);
                }
            }
        } else {
            this.cache.clear();
        }
    }

    /**
     * Get data from cache if not expired
     */
    _getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;

        const { data, timestamp, ttl } = cached;
        if (Date.now() - timestamp < ttl) {
            return data;
        }

        this.cache.delete(key);
        return null;
    }

    /**
     * Store data in cache
     */
    _setCache(key, data, ttl) {
        this.cache.set(key, {
            data,
            timestamp: Date.now(),
            ttl
        });
    }

    /**
     * Generate cache key
     */
    _getCacheKey(method, endpoint) {
        return `${method}:${endpoint}`;
    }

    /**
     * Delay helper for retries
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Create singleton instance
const apiClient = new ApiClient();

// Export for use in other modules
window.apiClient = apiClient;
window.ApiError = ApiError;
