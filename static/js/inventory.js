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
    selectedItems: new Set(),
    watchlistOnly: false,
    compactMode: false,

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
                    // When filtering, preserve server sort order
                    this.applyFilters(true);
                }, 300);
            });
        }

        // Watchlist toggle button
        const watchlistToggle = document.getElementById('watchlist-toggle');
        if (watchlistToggle) {
            watchlistToggle.addEventListener('click', () => {
                this.watchlistOnly = !this.watchlistOnly;
                watchlistToggle.classList.toggle('active', this.watchlistOnly);
                // When filtering, preserve server sort order
                this.applyFilters(true);
            });
        }

        // Density toggle button
        const densityToggle = document.getElementById('density-toggle');
        if (densityToggle) {
            densityToggle.addEventListener('click', () => {
                this.compactMode = !this.compactMode;
                densityToggle.classList.toggle('compact', this.compactMode);
                this.updateGridDensity();
            });
        }

        // Filter dropdowns
        document.getElementById('stock-filter')?.addEventListener('change', () => this.applyFilters(true));
        document.getElementById('gender-filter')?.addEventListener('change', () => this.applyFilters(true));

        // Sort dropdown
        document.getElementById('sort-select')?.addEventListener('change', (e) => {
            const value = e.target.value;
            this.sortBy = value;
            // Reload from server with new sort parameters
            this.loadInventory();
        });

        // Sort direction toggle
        const sortDirectionToggle = document.getElementById('sort-direction-toggle');
        if (sortDirectionToggle) {
            sortDirectionToggle.addEventListener('click', () => {
                this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
                sortDirectionToggle.classList.toggle('desc', this.sortOrder === 'desc');
                // Reload from server with new sort order
                this.loadInventory();
            });
        }

        // Pagination
        document.getElementById('prev-page')?.addEventListener('click', () => this.changePage(-1));
        document.getElementById('next-page')?.addEventListener('click', () => this.changePage(1));
    },

    async loadInventory() {
        try {
            this.showLoading(true);

            // Pass sort parameters to API for proper server-side sorting
            const params = {
                sort_by: this.sortBy,
                sort_order: this.sortOrder,
                t: Date.now()
            };

            const data = await StockService.getFragrances(params);
            this.allItems = data.items || [];
            this.totalItems = data.total || 0;

            // Data from server is already sorted, so we pass skipSort flag
            this.applyFilters(true);
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

    applyFilters(skipSort = false) {
        // Get filter values
        const searchTerm = document.getElementById('inventory-search')?.value.toLowerCase() || '';
        const stockFilter = document.getElementById('stock-filter')?.value;
        const genderFilter = document.getElementById('gender-filter')?.value;

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

            // Gender filter
            if (genderFilter && item.gender !== genderFilter) {
                return false;
            }

            // Watchlist filter (from toggle button only)
            if (this.watchlistOnly && !item.is_watchlisted) {
                return false;
            }

            return true;
        });

        // Only sort if not already sorted by server
        if (!skipSort) {
            this.sortItems();
        }

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
                case 'parfumo_score':
                    // Handle null scores - put them at the end
                    aVal = a.parfumo_score ?? (this.sortOrder === 'desc' ? -Infinity : Infinity);
                    bVal = b.parfumo_score ?? (this.sortOrder === 'desc' ? -Infinity : Infinity);
                    break;
                case 'parfumo_votes':
                    // Handle null votes - put them at the end
                    aVal = a.parfumo_votes ?? (this.sortOrder === 'desc' ? -1 : Infinity);
                    bVal = b.parfumo_votes ?? (this.sortOrder === 'desc' ? -1 : Infinity);
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
        const watchlistStarClass = item.is_watchlisted ? 'active' : '';
        const isSelected = this.selectedItems.has(item.slug) ? 'selected' : '';
        const checkboxChecked = this.selectedItems.has(item.slug) ? 'checked' : '';

        // Build rating display if we have Parfumo score
        let ratingHtml = '';
        if (item.parfumo_score) {
            const votesDisplay = item.parfumo_votes
                ? `<span class="parfumo-votes">(${item.parfumo_votes.toLocaleString()} votes)</span>`
                : '';

            // Create link if we have a Parfumo URL
            const scoreContent = item.parfumo_url
                ? `<a href="${item.parfumo_url}" target="_blank" class="parfumo-link">
                     <span class="parfumo-score">${item.parfumo_score.toFixed(1)}/10</span>
                   </a>`
                : `<span class="parfumo-score">${item.parfumo_score.toFixed(1)}/10</span>`;

            ratingHtml = `
                <div class="item-rating">
                    <div class="rating-line">
                        <span class="parfumo-label">Parfumo:</span>
                        ${scoreContent}
                        ${votesDisplay}
                    </div>
                </div>
            `;
        }

        return `
            <div class="inventory-item ${stockClass} ${isSelected}" data-slug="${item.slug}">
                <input type="checkbox" class="item-checkbox" data-slug="${item.slug}" ${checkboxChecked}>
                <div class="watchlist-star ${watchlistStarClass}" data-slug="${item.slug}"></div>
                <div class="item-header">
                    <div>
                        <div class="item-name">${item.name}</div>
                        ${ratingHtml}
                    </div>
                </div>
                <div class="item-details">
                    <span class="stock-status ${stockClass}">
                        ${stockText}
                    </span>
                    <span class="item-price">${item.price || 'N/A'}</span>
                </div>
                <div class="item-actions">
                    <a href="${item.url}" target="_blank" class="btn btn-primary">View Product</a>
                </div>
            </div>
        `;
    },

    bindItemEvents() {
        // Watchlist stars
        document.querySelectorAll('.watchlist-star').forEach(star => {
            star.addEventListener('click', async (e) => {
                e.stopPropagation();
                const slug = e.target.dataset.slug;
                const item = this.allItems.find(i => i.slug === slug);

                if (item) {
                    await this.toggleWatchlist(slug, item.is_watchlisted);
                }
            });
        });

        // Selection checkboxes
        document.querySelectorAll('.item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const slug = e.target.dataset.slug;
                const itemElement = document.querySelector(`.inventory-item[data-slug="${slug}"]`);

                if (e.target.checked) {
                    this.selectedItems.add(slug);
                    itemElement?.classList.add('selected');
                } else {
                    this.selectedItems.delete(slug);
                    itemElement?.classList.remove('selected');
                }

                this.updateBulkActionsBar();
            });
        });
    },

    updateBulkActionsBar() {
        const bulkActions = document.getElementById('bulk-actions');
        const selectedCount = document.getElementById('selected-count');

        if (this.selectedItems.size > 0) {
            bulkActions?.classList.add('show');
            if (selectedCount) selectedCount.textContent = this.selectedItems.size;
        } else {
            bulkActions?.classList.remove('show');
        }
    },

    async toggleWatchlist(slug, isWatched) {
        try {
            console.log(`Toggling watchlist for ${slug}, currently watched: ${isWatched}`);
            const result = isWatched
                ? await WatchlistService.removeItem(slug)
                : await WatchlistService.addItem(slug);
            console.log('Watchlist update result:', result);

            // Update local data
            const item = this.allItems.find(i => i.slug === slug);
            if (item) {
                item.is_watchlisted = !isWatched;
                console.log(`Updated local item ${slug}, is_watchlisted now: ${item.is_watchlisted}`);
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

    updateGridDensity() {
        const grid = document.getElementById('inventory-grid');
        if (grid) {
            grid.classList.toggle('compact', this.compactMode);
        }
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
    },

    selectAll() {
        const currentPageItems = this.filteredItems.slice(
            (this.currentPage - 1) * this.itemsPerPage,
            this.currentPage * this.itemsPerPage
        );

        currentPageItems.forEach(item => {
            this.selectedItems.add(item.slug);
            const checkbox = document.querySelector(`.item-checkbox[data-slug="${item.slug}"]`);
            const itemElement = document.querySelector(`.inventory-item[data-slug="${item.slug}"]`);
            if (checkbox) checkbox.checked = true;
            itemElement?.classList.add('selected');
        });

        this.updateBulkActionsBar();
    },

    clearSelection() {
        this.selectedItems.clear();
        document.querySelectorAll('.item-checkbox').forEach(cb => cb.checked = false);
        document.querySelectorAll('.inventory-item').forEach(item => item.classList.remove('selected'));
        this.updateBulkActionsBar();
    },

    async bulkAddToWatchlist() {
        if (this.selectedItems.size === 0) return;

        try {
            const result = await WatchlistService.bulkAdd(Array.from(this.selectedItems));

            // Update local data
            this.selectedItems.forEach(slug => {
                const item = this.allItems.find(i => i.slug === slug);
                if (item) item.is_watchlisted = true;
            });

            // Re-render and clear selection
            this.clearSelection();
            this.applyFilters();

            if (window.showAlert) {
                showAlert(result.message, 'success');
            }
        } catch (error) {
            console.error('Error:', error);
            if (window.showAlert) {
                showAlert('Failed to add items to watchlist', 'error');
            }
        }
    },

    async bulkRemoveFromWatchlist() {
        if (this.selectedItems.size === 0) return;

        try {
            const result = await WatchlistService.bulkRemove(Array.from(this.selectedItems));

            // Update local data
            this.selectedItems.forEach(slug => {
                const item = this.allItems.find(i => i.slug === slug);
                if (item) item.is_watchlisted = false;
            });

            // Re-render and clear selection
            this.clearSelection();
            this.applyFilters();

            if (window.showAlert) {
                showAlert(result.message, 'success');
            }
        } catch (error) {
            console.error('Error:', error);
            if (window.showAlert) {
                showAlert('Failed to remove items from watchlist', 'error');
            }
        }
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