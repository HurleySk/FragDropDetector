class Router {
    constructor() {
        this.currentPage = 'dashboard';
        this.pages = ['dashboard', 'inventory', 'configuration'];
        this.init();
    }

    init() {
        this.bindNavigation();
        this.handleInitialRoute();
    }

    bindNavigation() {
        // Handle navigation clicks
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.getAttribute('data-page');
                this.navigateTo(page);
            });
        });

        // Handle browser back/forward
        window.addEventListener('popstate', (e) => {
            const page = e.state?.page || 'dashboard';
            this.showPage(page);
        });

        // Handle mobile menu toggle
        this.setupMobileMenu();
    }

    setupMobileMenu() {
        // Find existing mobile menu toggle
        const toggle = document.querySelector('.mobile-menu-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                const sidebar = document.querySelector('.sidebar');
                const isOpen = sidebar.classList.contains('open');

                sidebar.classList.toggle('open');
                toggle.classList.toggle('menu-open', !isOpen);
            });
        }

        // Close menu when clicking nav items on mobile
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    const sidebar = document.querySelector('.sidebar');
                    const toggle = document.querySelector('.mobile-menu-toggle');

                    sidebar.classList.remove('open');
                    if (toggle) {
                        toggle.classList.remove('menu-open');
                    }
                }
            });
        });
    }

    handleInitialRoute() {
        const hash = window.location.hash.slice(1) || 'dashboard';
        const page = this.pages.includes(hash) ? hash : 'dashboard';
        this.showPage(page);
    }

    navigateTo(page) {
        if (!this.pages.includes(page)) {
            console.error(`Unknown page: ${page}`);
            return;
        }

        // Update URL without page reload
        const url = `${window.location.pathname}#${page}`;
        window.history.pushState({ page }, '', url);

        this.showPage(page);
    }

    showPage(page) {
        if (this.currentPage === page) return;

        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-page') === page);
        });

        // Show/hide page content
        this.pages.forEach(p => {
            const content = document.getElementById(`${p}-content`);
            if (content) {
                content.classList.toggle('hidden', p !== page);
            }
        });

        // Update current page
        const previousPage = this.currentPage;
        this.currentPage = page;

        // Call page lifecycle methods
        this.onPageLeave(previousPage);
        this.onPageEnter(page);
    }

    onPageEnter(page) {
        // Call page-specific initialization
        switch (page) {
            case 'dashboard':
                if (typeof initializeDashboard === 'function') {
                    initializeDashboard();
                }
                break;
            case 'inventory':
                if (window.InventoryManager) {
                    window.InventoryManager.init();
                }
                break;
            case 'configuration':
                if (typeof initializeConfiguration === 'function') {
                    // Call the function and handle async if it returns a promise
                    const result = initializeConfiguration();
                    if (result && typeof result.catch === 'function') {
                        result.catch(err => {
                            console.error('Failed to initialize configuration:', err);
                        });
                    }
                }
                break;
        }

        // Update page title
        const titles = {
            dashboard: 'Dashboard - FragDropDetector',
            inventory: 'Inventory - FragDropDetector',
            configuration: 'Configuration - FragDropDetector'
        };
        document.title = titles[page] || 'FragDropDetector';
    }

    onPageLeave(page) {
        // Cleanup page-specific resources
        switch (page) {
            case 'dashboard':
                if (typeof cleanupDashboard === 'function') {
                    cleanupDashboard();
                }
                break;
            case 'inventory':
                // Inventory cleanup if needed
                break;
            case 'configuration':
                if (typeof cleanupConfiguration === 'function') {
                    cleanupConfiguration();
                }
                break;
        }
    }

    getCurrentPage() {
        return this.currentPage;
    }
}

// Global navigation function
function navigateToPage(page) {
    if (window.router) {
        window.router.navigateTo(page);
    }
}

// Initialize router when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.router = new Router();
});

// Export for use in other scripts
window.Router = Router;