// Inventory Management Module
const InventoryManager = {
    currentPage: 1,
    itemsPerPage: 24,
    totalItems: 0,
    allItems: [],
    filteredItems: [],
    searchTimeout: null,
    sortBy: 'name',
    sortOrder: 'asc',

    init() {
        this.bindEvents();
        this.loadInventory();
    },

    bindEvents() {
        // Search input with debounce
        const searchInput = document.getElementById('inventory-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.applyFilters();
                }, 300);
            });
        }

        // Filter dropdowns
        document.getElementById('stock-filter')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('watchlist-filter')?.addEventListener('change', () => this.applyFilters());

        // Sort dropdown
        document.getElementById('sort-select')?.addEventListener('change', (e) => {
            const value = e.target.value;
            this.sortBy = value;
            this.applyFilters();
        });

        // Pagination
        document.getElementById('prev-page')?.addEventListener('click', () => this.changePage(-1));
        document.getElementById('next-page')?.addEventListener('click', () => this.changePage(1));
    },

    async loadInventory() {
        try {
            this.showLoading(true);

            const response = await fetch('/api/stock/fragrances');
            if (!response.ok) throw new Error('Failed to load inventory');

            const data = await response.json();
            this.allItems = data.items || [];
            this.totalItems = data.total || 0;

            this.applyFilters();
            this.updateStats();

        } catch (error) {
            console.error('Error loading inventory:', error);
            if (window.showAlert) {
                showAlert('Failed to load inventory', 'error');
            } else {
                console.error('Failed to load inventory');
            }
        } finally {
            this.showLoading(false);
        }
    },

    applyFilters() {
        // Get filter values
        const searchTerm = document.getElementById('inventory-search')?.value.toLowerCase() || '';
        const stockFilter = document.getElementById('stock-filter')?.value;
        const watchlistFilter = document.getElementById('watchlist-filter')?.value;

        // Filter items
        this.filteredItems = this.allItems.filter(item => {
            // Search filter
            if (searchTerm &&
                !item.name.toLowerCase().includes(searchTerm) &&
                !item.slug.toLowerCase().includes(searchTerm)) {
                return false;
            }

            // Stock filter
            if (stockFilter !== '' && stockFilter !== null) {
                const inStock = stockFilter === 'true';
                if (item.in_stock !== inStock) return false;
            }

            // Watchlist filter
            if (watchlistFilter === 'true' && !item.is_watchlisted) {
                return false;
            }

            return true;
        });

        // Sort items
        this.sortItems();

        // Reset to first page
        this.currentPage = 1;

        // Render the grid
        this.renderGrid();
        this.updatePagination();
        this.updateStats();
    },

    sortItems() {
        this.filteredItems.sort((a, b) => {
            let aVal, bVal;

            switch (this.sortBy) {
                case 'price':
                    aVal = this.parsePrice(a.price);
                    bVal = this.parsePrice(b.price);
                    break;
                case 'in_stock':
                    aVal = a.in_stock ? 1 : 0;
                    bVal = b.in_stock ? 1 : 0;
                    break;
                default:
                    aVal = a[this.sortBy]?.toLowerCase() || '';
                    bVal = b[this.sortBy]?.toLowerCase() || '';
            }

            if (aVal < bVal) return this.sortOrder === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortOrder === 'asc' ? 1 : -1;
            return 0;
        });
    },

    parsePrice(price) {
        if (!price || price === 'N/A') return Number.MAX_VALUE;
        return parseFloat(price.replace(/[^0-9.]/g, '')) || Number.MAX_VALUE;
    },

    renderGrid() {
        const grid = document.getElementById('inventory-grid');
        const noResults = document.getElementById('no-results');

        if (!grid) return;

        if (this.filteredItems.length === 0) {
            grid.innerHTML = '';
            noResults?.classList.remove('hidden');
            return;
        }

        noResults?.classList.add('hidden');

        // Calculate page items
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pageItems = this.filteredItems.slice(startIndex, endIndex);

        // Render items
        grid.innerHTML = pageItems.map(item => this.renderItem(item)).join('');

        // Bind item event handlers
        this.bindItemEvents();
    },

    renderItem(item) {
        const stockClass = item.in_stock ? 'in-stock' : 'out-of-stock';
        const stockText = item.in_stock ? 'In Stock' : 'Out of Stock';
        const watchlistBadge = item.is_watchlisted ? '<span class="watchlist-badge">Watching</span>' : '';
        const watchlistBtnText = item.is_watchlisted ? 'Unwatch' : 'Watch';
        const watchlistBtnClass = item.is_watchlisted ? 'watching' : '';

        return `
            <div class="inventory-item ${stockClass}" data-slug="${item.slug}">
                ${watchlistBadge}
                <div class="item-header">
                    <div>
                        <div class="item-name">${item.name}</div>
                        <div class="item-slug">${item.slug}</div>
                    </div>
                </div>
                <div class="item-details">
                    <span class="stock-status ${stockClass}">
                        ${stockText}
                    </span>
                    <span class="item-price">${item.price || 'N/A'}</span>
                </div>
                <div class="item-actions">
                    <button class="watchlist-btn ${watchlistBtnClass}" data-slug="${item.slug}">
                        ${watchlistBtnText}
                    </button>
                    <a href="${item.url}" target="_blank" class="view-btn">View</a>
                </div>
            </div>
        `;
    },

    bindItemEvents() {
        // Watchlist buttons
        document.querySelectorAll('.watchlist-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const slug = e.target.dataset.slug;
                const item = this.allItems.find(i => i.slug === slug);

                if (item) {
                    await this.toggleWatchlist(slug, item.is_watchlisted);
                }
            });
        });
    },

    async toggleWatchlist(slug, isWatched) {
        try {
            const endpoint = isWatched ? '/api/stock/watchlist/remove' : '/api/stock/watchlist/add';
            const response = await fetch(`${endpoint}/${slug}`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Failed to update watchlist');

            const result = await response.json();

            // Update local data
            const item = this.allItems.find(i => i.slug === slug);
            if (item) {
                item.is_watchlisted = !isWatched;
            }

            // Re-render
            this.applyFilters();

            if (window.showAlert) {
                showAlert(result.message, 'success');
            }

        } catch (error) {
            console.error('Error updating watchlist:', error);
            if (window.showAlert) {
                showAlert('Failed to update watchlist', 'error');
            } else {
                console.error('Failed to update watchlist');
            }
        }
    },

    changePage(delta) {
        const totalPages = Math.ceil(this.filteredItems.length / this.itemsPerPage);
        const newPage = this.currentPage + delta;

        if (newPage >= 1 && newPage <= totalPages) {
            this.currentPage = newPage;
            this.renderGrid();
            this.updatePagination();

            // Scroll to top of grid
            document.getElementById('inventory-content')?.scrollIntoView({ behavior: 'smooth' });
        }
    },

    updatePagination() {
        const totalPages = Math.ceil(this.filteredItems.length / this.itemsPerPage) || 1;

        document.getElementById('current-page').textContent = this.currentPage;
        document.getElementById('total-pages').textContent = totalPages;

        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');

        if (prevBtn) prevBtn.disabled = this.currentPage === 1;
        if (nextBtn) nextBtn.disabled = this.currentPage === totalPages;
    },

    updateStats() {
        const inStock = this.allItems.filter(i => i.in_stock).length;
        const outOfStock = this.allItems.length - inStock;
        const watchlist = this.allItems.filter(i => i.is_watchlisted).length;

        document.getElementById('total-count').textContent = this.allItems.length;
        document.getElementById('in-stock-count').textContent = inStock;
        document.getElementById('out-stock-count').textContent = outOfStock;
        document.getElementById('watchlist-count').textContent = watchlist;
    },

    showLoading(show) {
        const loading = document.getElementById('inventory-loading');
        const grid = document.getElementById('inventory-grid');

        if (show) {
            loading?.classList.remove('hidden');
            if (grid) grid.style.display = 'none';
        } else {
            loading?.classList.add('hidden');
            if (grid) grid.style.display = 'grid';
        }
    },

    refresh() {
        this.loadInventory();
    }
};

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if on inventory page
    if (window.location.hash === '#inventory' || !window.location.hash) {
        // Will be initialized by router
    }
});

// Export for use in other modules
window.InventoryManager = InventoryManager;