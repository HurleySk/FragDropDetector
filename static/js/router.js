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
        // Handle navigation clicks (both sidebar and bottom nav)
        document.querySelectorAll('.nav-item, .bottom-nav-item').forEach(item => {
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

        // Update navigation (both sidebar and bottom nav)
        document.querySelectorAll('.nav-item, .bottom-nav-item').forEach(item => {
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