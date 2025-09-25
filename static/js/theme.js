// Lightweight Theme Management

class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.createToggleButton();
        this.bindEvents();
    }

    getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    getStoredTheme() {
        return localStorage.getItem('theme');
    }

    setStoredTheme(theme) {
        localStorage.setItem('theme', theme);
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        this.updateToggleButton();
    }

    toggle() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
        this.setStoredTheme(newTheme);
    }

    createToggleButton() {
        const button = document.createElement('button');
        button.className = 'theme-toggle';
        button.setAttribute('aria-label', 'Toggle theme');
        button.id = 'theme-toggle';
        document.body.appendChild(button);
    }

    updateToggleButton() {
        const button = document.getElementById('theme-toggle');
        if (button) {
            // Use reliable text-based icons
            button.innerHTML = this.currentTheme === 'dark' ? '◯' : '●';
            button.title = this.currentTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
        }
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            if (e.target.id === 'theme-toggle') {
                this.toggle();
            }
        });

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!this.getStoredTheme()) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
}

// Initialize theme manager
window.themeManager = new ThemeManager();