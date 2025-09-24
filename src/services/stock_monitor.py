"""
Stock monitor for Montagne Parfums fragrance inventory
Tracks product availability and price changes
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class FragranceProduct:
    """Represents a fragrance product"""

    def __init__(self, name: str, url: str, price: str, in_stock: bool):
        self.name = name.strip()
        self.url = url
        self.price = price.strip()
        self.in_stock = in_stock
        self.slug = self._extract_slug_from_url(url)

    def _extract_slug_from_url(self, url: str) -> str:
        """Extract product slug from URL"""
        if url.startswith('/fragrance/'):
            return url.replace('/fragrance/', '')
        return url.split('/')[-1] if '/' in url else url

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'slug': self.slug,
            'url': self.url,
            'price': self.price,
            'in_stock': self.in_stock
        }


class StockMonitor:
    """Monitors Montagne Parfums stock levels"""

    def __init__(self):
        self.base_url = "https://www.montagneparfums.com"
        self.fragrance_url = f"{self.base_url}/fragrance"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_page(self) -> Optional[str]:
        """Fetch the fragrance page HTML"""
        try:
            logger.info(f"Fetching {self.fragrance_url}")
            response = self.session.get(self.fragrance_url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching fragrance page: {e}")
            return None

    def parse_products(self, html: str) -> List[FragranceProduct]:
        """Parse products from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            products = []

            # The site uses JavaScript to load content, so we need to look for product data
            # in script tags or data attributes

            # Try to find product data in script tags
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'fragrance' in script.string.lower():
                    # Look for JSON data structures
                    import json
                    try:
                        # Try to extract JSON-like structures
                        script_content = script.string
                        if 'products' in script_content or 'collection' in script_content:
                            logger.debug(f"Found potential product data in script tag")
                            # This would need more specific parsing based on actual site structure
                    except:
                        continue

            # Alternative approach: try to find product information in the grid structure
            # even if links are empty
            grid = soup.find('div', class_='ProductList-grid')
            if grid:
                # Look for any elements that might contain product info
                product_containers = grid.find_all('div', class_=lambda x: x and 'product' in x.lower())
                if not product_containers:
                    # Try looking for any divs within the grid
                    product_containers = grid.find_all('div')

                logger.info(f"Found {len(product_containers)} potential product containers")

                # Since the site uses JavaScript, we'll create dummy products based on URLs
                # This is a fallback approach
                product_links = grid.find_all('a', href=re.compile(r'^/fragrance/'))
                for link in product_links:
                    try:
                        href = link.get('href')
                        if href:
                            slug = href.replace('/fragrance/', '')
                            # Create product with basic info - name from slug
                            name = slug.replace('-', ' ').title()
                            product = FragranceProduct(
                                name=name,
                                url=href,
                                price="N/A",  # Price not available without JavaScript
                                in_stock=True  # Assume in stock if listed
                            )
                            products.append(product)
                    except Exception as e:
                        logger.warning(f"Error parsing product link: {e}")
                        continue

            logger.info(f"Parsed {len(products)} products")
            return products

        except Exception as e:
            logger.error(f"Error parsing products: {e}")
            return []

    def _parse_single_product(self, link_element) -> Optional[FragranceProduct]:
        """Parse a single product from a link element"""
        url = link_element.get('href')
        if not url:
            return None

        # Get text content and split lines
        text_content = link_element.get_text(separator='\n').strip()
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]

        if len(lines) < 2:
            return None

        # Extract name and price
        name = lines[0]
        price_line = lines[-1]

        # Check for sold out status
        in_stock = True
        sold_out_indicators = ['sold out', 'out of stock', 'unavailable']
        for line in lines:
            if any(indicator in line.lower() for indicator in sold_out_indicators):
                in_stock = False
                break

        # Extract price (look for $ followed by digits)
        price = "N/A"
        price_match = re.search(r'\$[\d,]+\.?\d*', price_line)
        if price_match:
            price = price_match.group()

        return FragranceProduct(name, url, price, in_stock)

    def get_current_stock(self) -> Dict[str, FragranceProduct]:
        """Get current stock as a dictionary keyed by product slug"""
        html = self.fetch_page()
        if not html:
            return {}

        products = self.parse_products(html)
        return {product.slug: product for product in products}

    def compare_stock(self, previous_stock: Dict[str, FragranceProduct],
                     current_stock: Dict[str, FragranceProduct]) -> Dict:
        """Compare two stock snapshots and find changes"""
        changes = {
            'new_products': [],
            'removed_products': [],
            'restocked': [],
            'out_of_stock': [],
            'price_changes': []
        }

        # Find new and removed products
        previous_slugs = set(previous_stock.keys())
        current_slugs = set(current_stock.keys())

        new_slugs = current_slugs - previous_slugs
        removed_slugs = previous_slugs - current_slugs

        for slug in new_slugs:
            changes['new_products'].append(current_stock[slug])

        for slug in removed_slugs:
            changes['removed_products'].append(previous_stock[slug])

        # Find stock and price changes
        common_slugs = previous_slugs & current_slugs
        for slug in common_slugs:
            prev_product = previous_stock[slug]
            curr_product = current_stock[slug]

            # Stock status changes
            if not prev_product.in_stock and curr_product.in_stock:
                changes['restocked'].append(curr_product)
            elif prev_product.in_stock and not curr_product.in_stock:
                changes['out_of_stock'].append(curr_product)

            # Price changes
            if prev_product.price != curr_product.price and curr_product.price != "N/A":
                changes['price_changes'].append({
                    'product': curr_product,
                    'old_price': prev_product.price,
                    'new_price': curr_product.price
                })

        return changes

    def format_changes_summary(self, changes: Dict) -> str:
        """Format changes into a readable summary"""
        summary_parts = []

        if changes['new_products']:
            summary_parts.append(f"{len(changes['new_products'])} new products")

        if changes['removed_products']:
            summary_parts.append(f"{len(changes['removed_products'])} removed products")

        if changes['restocked']:
            summary_parts.append(f"{len(changes['restocked'])} restocked")

        if changes['out_of_stock']:
            summary_parts.append(f"{len(changes['out_of_stock'])} out of stock")

        if changes['price_changes']:
            summary_parts.append(f"{len(changes['price_changes'])} price changes")

        if not summary_parts:
            return "No changes detected"

        return "Stock changes: " + ", ".join(summary_parts)


def main():
    """Test the stock monitor"""
    logging.basicConfig(level=logging.INFO)

    monitor = StockMonitor()
    stock = monitor.get_current_stock()

    print(f"Found {len(stock)} products")

    # Show first 5 products
    for i, (slug, product) in enumerate(stock.items()):
        if i >= 5:
            break
        status = "In Stock" if product.in_stock else "Out of Stock"
        print(f"  {product.name} - {product.price} - {status}")


if __name__ == "__main__":
    main()