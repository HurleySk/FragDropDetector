/**
 * Reactive State Management for FragDropDetector
 * Provides centralized state with reactivity and persistence
 */

class StateStore {
    constructor() {
        this.state = {
            status: null,
            drops: [],
            stockChanges: [],
            fragrances: {},
            watchlist: [],
            config: null,
            lastUpdate: null
        };

        this.listeners = new Map();
        this.loadFromStorage();
    }

    /**
     * Get current state value
     */
    get(key) {
        return this.state[key];
    }

    /**
     * Set state value and notify listeners
     */
    set(key, value) {
        const oldValue = this.state[key];
        this.state[key] = value;
        this.state.lastUpdate = Date.now();

        this.saveToStorage();
        this.notify(key, value, oldValue);
    }

    /**
     * Update nested state
     */
    update(key, updater) {
        const current = this.state[key];
        const updated = typeof updater === 'function' ? updater(current) : updater;
        this.set(key, updated);
    }

    /**
     * Subscribe to state changes
     */
    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, new Set());
        }
        this.listeners.get(key).add(callback);

        return () => {
            this.listeners.get(key)?.delete(callback);
        };
    }

    /**
     * Notify all listeners for a key
     */
    notify(key, newValue, oldValue) {
        this.listeners.get(key)?.forEach(callback => {
            try {
                callback(newValue, oldValue);
            } catch (error) {
                console.error(`Error in state listener for ${key}:`, error);
            }
        });

        this.listeners.get('*')?.forEach(callback => {
            try {
                callback(key, newValue, oldValue);
            } catch (error) {
                console.error('Error in global state listener:', error);
            }
        });
    }

    /**
     * Clear specific state key
     */
    clear(key) {
        this.set(key, null);
    }

    /**
     * Reset all state
     */
    reset() {
        Object.keys(this.state).forEach(key => {
            if (key !== 'lastUpdate') {
                this.state[key] = null;
            }
        });
        this.clearStorage();
        this.notify('*', null, null);
    }

    /**
     * Load state from localStorage
     */
    loadFromStorage() {
        try {
            const stored = localStorage.getItem('fragdrop_state');
            if (stored) {
                const parsed = JSON.parse(stored);
                Object.assign(this.state, parsed);
            }
        } catch (error) {
            console.warn('Failed to load state from storage:', error);
        }
    }

    /**
     * Save state to localStorage
     */
    saveToStorage() {
        try {
            const serializable = {
                watchlist: this.state.watchlist,
                lastUpdate: this.state.lastUpdate
            };
            localStorage.setItem('fragdrop_state', JSON.stringify(serializable));
        } catch (error) {
            console.warn('Failed to save state to storage:', error);
        }
    }

    /**
     * Clear localStorage
     */
    clearStorage() {
        try {
            localStorage.removeItem('fragdrop_state');
        } catch (error) {
            console.warn('Failed to clear storage:', error);
        }
    }

    /**
     * Get state snapshot
     */
    getSnapshot() {
        return { ...this.state };
    }

    /**
     * Check if state is stale
     */
    isStale(maxAge = 30000) {
        if (!this.state.lastUpdate) return true;
        return Date.now() - this.state.lastUpdate > maxAge;
    }
}

/**
 * Cache manager for API responses
 */
class CacheManager {
    constructor(defaultTTL = 30000) {
        this.cache = new Map();
        this.defaultTTL = defaultTTL;
    }

    /**
     * Get cached value
     */
    get(key) {
        const entry = this.cache.get(key);
        if (!entry) return null;

        if (Date.now() > entry.expires) {
            this.cache.delete(key);
            return null;
        }

        return entry.value;
    }

    /**
     * Set cached value
     */
    set(key, value, ttl = this.defaultTTL) {
        this.cache.set(key, {
            value,
            expires: Date.now() + ttl
        });
    }

    /**
     * Check if key exists and is valid
     */
    has(key) {
        return this.get(key) !== null;
    }

    /**
     * Invalidate cache entry
     */
    invalidate(key) {
        this.cache.delete(key);
    }

    /**
     * Invalidate all cache entries matching pattern
     */
    invalidatePattern(pattern) {
        const regex = new RegExp(pattern);
        for (const key of this.cache.keys()) {
            if (regex.test(key)) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * Clear all cache
     */
    clear() {
        this.cache.clear();
    }

    /**
     * Clean expired entries
     */
    cleanup() {
        const now = Date.now();
        for (const [key, entry] of this.cache.entries()) {
            if (now > entry.expires) {
                this.cache.delete(key);
            }
        }
    }
}

// Global instances
const store = new StateStore();
const cache = new CacheManager();

// Auto-cleanup cache every minute
setInterval(() => cache.cleanup(), 60000);

// Export for use in other modules
window.StateStore = StateStore;
window.CacheManager = CacheManager;
window.store = store;
window.cache = cache;
