/**
 * Theme Configuration Manager
 * Handles dark/light mode preferences with system detection
 */

class ThemeManager {
    constructor() {
        this.storageKey = 'fragdrop-theme-preference';
        this.init();
    }

    init() {
        // Get saved preference or default to 'system'
        const savedTheme = localStorage.getItem(this.storageKey) || 'system';
        this.applyTheme(savedTheme);

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (this.getCurrentPreference() === 'system') {
                this.applyTheme('system');
            }
        });
    }

    getCurrentPreference() {
        return localStorage.getItem(this.storageKey) || 'system';
    }

    setTheme(preference) {
        localStorage.setItem(this.storageKey, preference);
        this.applyTheme(preference);

        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: preference, actualTheme: this.getActualTheme() }
        }));
    }

    applyTheme(preference) {
        const html = document.documentElement;

        // Remove existing theme attributes
        html.removeAttribute('data-theme');

        if (preference === 'dark') {
            html.setAttribute('data-theme', 'dark');
        } else if (preference === 'light') {
            html.setAttribute('data-theme', 'light');
        }
        // For 'system', we rely on CSS media query
    }

    getActualTheme() {
        const preference = this.getCurrentPreference();

        if (preference === 'system') {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }

        return preference;
    }

    getAvailableThemes() {
        return [
            { value: 'system', label: 'System Default', description: 'Matches your device setting' },
            { value: 'light', label: 'Light Mode', description: 'Always use light theme' },
            { value: 'dark', label: 'Dark Mode', description: 'Always use dark theme' }
        ];
    }
}

// Initialize theme manager
const themeManager = new ThemeManager();

// Export for use in other scripts
window.themeManager = themeManager;