"""
Enhanced Stock Monitor with Playwright for JavaScript-rendered sites
Includes retry logic, caching, and user-specific watchlists
"""

import logging
import asyncio
import json
import time
import hashlib
from typing import List, Dict, Optional, Set, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import pickle
import re

from playwright.async_api import async_playwright, Browser, Page, TimeoutError

logger = logging.getLogger(__name__)


@dataclass
class FragranceProduct:
    """Represents a fragrance product"""
    name: str
    slug: str
    url: str
    price: str
    in_stock: bool
    image_url: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = asdict(self)
        if self.last_updated:
            data['last_updated'] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'FragranceProduct':
        """Create from dictionary"""
        if 'last_updated' in data and data['last_updated']:
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


class ProductCache:
    """Simple file-based cache for product data"""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "stock_cache.pkl"
        self.ttl = timedelta(minutes=15)  # Cache for 15 minutes

    def get(self, key: str) -> Optional[Dict[str, FragranceProduct]]:
        """Get cached data if not expired"""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'rb') as f:
                cache_data = pickle.load(f)

            if key in cache_data:
                timestamp, data = cache_data[key]
                if datetime.now() - timestamp < self.ttl:
                    logger.info(f"Cache hit for {key}")
                    return data
                else:
                    logger.info(f"Cache expired for {key}")
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    def set(self, key: str, data: Dict[str, FragranceProduct]):
        """Store data in cache"""
        cache_data = {}

        # Load existing cache
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
            except:
                pass

        # Update cache
        cache_data[key] = (datetime.now(), data)

        # Save cache
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.info(f"Cached data for {key}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def clear(self):
        """Clear all cached data"""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Cache cleared")


class RetryStrategy:
    """Exponential backoff retry strategy"""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = 30.0

    async def execute(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None
        delay = self.initial_delay

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self.max_delay)  # Exponential backoff
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")

        raise last_exception


class EnhancedStockMonitor:
    """Enhanced stock monitor with Playwright, caching, and retry logic"""

    def __init__(self, use_cache: bool = True, headless: bool = True):
        self.base_url = "https://www.montagneparfums.com"
        self.fragrance_url = f"{self.base_url}/fragrance"
        self.cache = ProductCache() if use_cache else None
        self.retry_strategy = RetryStrategy()
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.watchlist: Set[str] = set()  # Product slugs to specifically monitor

    def add_to_watchlist(self, product_slugs: List[str]):
        """Add products to watchlist for priority monitoring"""
        self.watchlist.update(product_slugs)
        logger.info(f"Added {len(product_slugs)} products to watchlist")

    def remove_from_watchlist(self, product_slugs: List[str]):
        """Remove products from watchlist"""
        for slug in product_slugs:
            self.watchlist.discard(slug)
        logger.info(f"Removed {len(product_slugs)} products from watchlist")

    async def _init_browser(self):
        """Initialize Playwright browser"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            logger.info("Browser initialized")

    async def _create_page(self) -> Page:
        """Create a new browser page with stealth settings"""
        await self._init_browser()
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # Add stealth mode to avoid detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        """)

        return page

    async def _fetch_and_parse_products(self, url: str) -> List[FragranceProduct]:
        """Fetch page and parse products directly"""
        async def fetch():
            page = await self._create_page()
            try:
                logger.info(f"Fetching {url}")
                await page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait for content to load
                await page.wait_for_selector('.ProductList-grid', timeout=10000)

                # Scroll to load lazy-loaded content
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1)  # Wait for lazy loading

                # Parse products directly from the page
                products = []

                # Get all product items from the grid
                product_elements = await page.query_selector_all('.ProductList-item')

                if not product_elements:
                    # Fallback to link-based selection
                    logger.warning("No .ProductList-item found, trying fallback selector")
                    product_elements = await page.query_selector_all('a[href*="/fragrance/"]')

                logger.info(f"Found {len(product_elements)} product elements")

                for element in product_elements:
                    try:
                        # Get the product link
                        link_elem = await element.query_selector('a[href*="/fragrance/"]')

                        # If element itself is a link
                        if not link_elem:
                            tag_name = await element.evaluate('el => el.tagName')
                            if tag_name == 'A':
                                link_elem = element

                        if not link_elem:
                            continue

                        href = await link_elem.get_attribute('href')
                        if not href or '/fragrance/' not in href:
                            continue

                        # Extract slug from URL
                        slug = href.split('/fragrance/')[-1].split('?')[0]

                        # Get product name
                        name_elem = await element.query_selector('.ProductList-title')
                        if not name_elem:
                            name_elem = await element.query_selector('h1, h2, h3, .product-title')

                        name = await name_elem.text_content() if name_elem else slug.replace('-', ' ')
                        name = name.strip() if name else slug.replace('-', ' ')

                        # Get price
                        price_elem = await element.query_selector('.product-price, .ProductList-price')
                        price = await price_elem.text_content() if price_elem else 'N/A'
                        price = price.strip() if price else 'N/A'

                        # Clean up price
                        price_match = re.search(r'\$[\d,]+\.?\d*', price)
                        if price_match:
                            price = price_match.group()
                        elif price == '' or not price:
                            price = 'N/A'

                        # Check for sold out indicator - THIS IS THE FIX
                        sold_out_elem = await element.query_selector('.product-mark.sold-out')
                        in_stock = sold_out_elem is None

                        # Get image URL if available
                        img_elem = await element.query_selector('img')
                        image_url = None
                        if img_elem:
                            image_url = await img_elem.get_attribute('src') or await img_elem.get_attribute('data-src')

                        # Create product object
                        product = FragranceProduct(
                            name=name,
                            slug=slug,
                            url=f"{self.base_url}{href}" if not href.startswith('http') else href,
                            price=price,
                            in_stock=in_stock,
                            image_url=image_url,
                            last_updated=datetime.now()
                        )
                        products.append(product)

                    except Exception as e:
                        logger.warning(f"Error parsing product element: {e}")
                        continue

                in_stock_count = sum(1 for p in products if p.in_stock)
                out_of_stock_count = sum(1 for p in products if not p.in_stock)
                logger.info(f"Parsed {len(products)} products - {in_stock_count} in stock, {out_of_stock_count} out of stock")

                return products

            finally:
                await page.close()

        return await self.retry_strategy.execute(fetch)

    async def get_current_stock(self, force_refresh: bool = False) -> Dict[str, FragranceProduct]:
        """Get current stock with caching support"""
        cache_key = "montagne_stock"

        # Check cache first
        if not force_refresh and self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        # Fetch fresh data
        try:
            products = await self._fetch_and_parse_products(self.fragrance_url)

            # Convert to dictionary
            stock_dict = {p.slug: p for p in products}

            # Cache the results
            if self.cache:
                self.cache.set(cache_key, stock_dict)

            return stock_dict

        except Exception as e:
            logger.error(f"Failed to get current stock: {e}")
            # Return cached data if available, even if expired
            if self.cache:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    logger.warning("Returning expired cache due to fetch failure")
                    return cached_data
            return {}

    async def get_product_details(self, product_slug: str) -> Optional[FragranceProduct]:
        """Get detailed information for a specific product"""
        url = f"{self.base_url}/fragrance/{product_slug}"

        try:
            page = await self._create_page()
            await page.goto(url, wait_until='networkidle')

            # Extract detailed product info
            product_data = await page.evaluate('''() => {
                const getText = (selector) => {
                    const el = document.querySelector(selector);
                    return el ? el.textContent.trim() : '';
                };

                return {
                    name: getText('h1, .product-title'),
                    price: getText('.product-price, .price'),
                    description: getText('.product-description, .description'),
                    size: getText('.product-size, .size'),
                    inStock: !document.body.textContent.toLowerCase().includes('sold out')
                };
            }''')

            await page.close()

            return FragranceProduct(
                name=product_data['name'],
                slug=product_slug,
                url=url,
                price=product_data['price'],
                in_stock=product_data['inStock'],
                size=product_data.get('size'),
                description=product_data.get('description'),
                last_updated=datetime.now()
            )

        except Exception as e:
            logger.error(f"Failed to get product details for {product_slug}: {e}")
            return None

    async def monitor_watchlist(self) -> Dict[str, FragranceProduct]:
        """Monitor only products in the watchlist"""
        if not self.watchlist:
            logger.warning("Watchlist is empty")
            return {}

        results = {}
        for slug in self.watchlist:
            product = await self.get_product_details(slug)
            if product:
                results[slug] = product

        return results

    def compare_stock(self, previous: Dict[str, FragranceProduct],
                     current: Dict[str, FragranceProduct]) -> Dict:
        """Compare two stock snapshots and find changes"""
        changes = {
            'new_products': [],
            'removed_products': [],
            'restocked': [],
            'out_of_stock': [],
            'price_changes': [],
            'watchlist_changes': []
        }

        prev_slugs = set(previous.keys())
        curr_slugs = set(current.keys())

        # New and removed products
        for slug in curr_slugs - prev_slugs:
            changes['new_products'].append(current[slug])
            if slug in self.watchlist:
                changes['watchlist_changes'].append(('new', current[slug]))

        for slug in prev_slugs - curr_slugs:
            changes['removed_products'].append(previous[slug])
            if slug in self.watchlist:
                changes['watchlist_changes'].append(('removed', previous[slug]))

        # Check changes in existing products
        for slug in prev_slugs & curr_slugs:
            prev_product = previous[slug]
            curr_product = current[slug]

            # Stock status changes
            if not prev_product.in_stock and curr_product.in_stock:
                changes['restocked'].append(curr_product)
                if slug in self.watchlist:
                    changes['watchlist_changes'].append(('restocked', curr_product))
            elif prev_product.in_stock and not curr_product.in_stock:
                changes['out_of_stock'].append(curr_product)
                if slug in self.watchlist:
                    changes['watchlist_changes'].append(('out_of_stock', curr_product))

            # Price changes
            if prev_product.price != curr_product.price and curr_product.price != "N/A":
                change_info = {
                    'product': curr_product,
                    'old_price': prev_product.price,
                    'new_price': curr_product.price
                }
                changes['price_changes'].append(change_info)
                if slug in self.watchlist:
                    changes['watchlist_changes'].append(('price_change', change_info))

        return changes

    async def cleanup(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            logger.info("Browser closed")


async def main():
    """Test the enhanced stock monitor"""
    logging.basicConfig(level=logging.INFO)

    monitor = EnhancedStockMonitor(headless=True, use_cache=False)

    try:
        # Get all stock
        logger.info("Fetching all stock...")
        stock = await monitor.get_current_stock()
        logger.info(f"Found {len(stock)} products")

        # Count stock status
        in_stock = sum(1 for p in stock.values() if p.in_stock)
        out_of_stock = len(stock) - in_stock

        print(f"\nStock Summary:")
        print(f"Total Products: {len(stock)}")
        print(f"In Stock: {in_stock}")
        print(f"Out of Stock: {out_of_stock}")

        # Show first 5 out of stock products
        print("\nSample Out of Stock Products:")
        count = 0
        for slug, product in stock.items():
            if not product.in_stock and count < 5:
                print(f"  - {product.name} ({slug})")
                count += 1

        # Show first 5 in stock products
        print("\nSample In Stock Products:")
        count = 0
        for slug, product in stock.items():
            if product.in_stock and count < 5:
                print(f"  - {product.name} ({slug})")
                count += 1

    finally:
        await monitor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())