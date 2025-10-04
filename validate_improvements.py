#!/usr/bin/env python3
"""
Validation script for Parfumo matching improvements
Tests the new database-backed system with improved extraction and fuzzy matching
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.fragrance_mapper import get_fragrance_mapper
from models.database import Database

def test_database_schema():
    """Test that new database fields exist"""
    print("\n=== Testing Database Schema ===")

    db = Database()
    session = db.get_session()

    try:
        from models.database import FragranceStock
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('fragrance_stock')]

        required_fields = [
            'original_brand',
            'original_name',
            'parfumo_id',
            'parfumo_score',
            'parfumo_votes',
            'parfumo_not_found',
            'last_searched',
            'rating_last_updated'
        ]

        missing = [f for f in required_fields if f not in columns]

        if missing:
            print(f"❌ Missing fields: {missing}")
            return False
        else:
            print(f"✅ All required fields present: {required_fields}")
            return True

    finally:
        session.close()


def test_multi_word_brand_extraction():
    """Test extraction of multi-word brands"""
    print("\n=== Testing Multi-word Brand Extraction ===")

    mapper = get_fragrance_mapper()

    test_cases = [
        ("VANILLE FRAICHE INSPIRED BY PARFUMS DE MARLY LAYTON", "Parfums de Marly", "Layton"),
        ("GENTLE SILVER INSPIRED BY MFK GENTLE FLUIDITY SILVER", "Maison Francis Kurkdjian", "Gentle Fluidity Silver"),
        ("IMAGINARY INSPIRED BY LOUIS VUITTON IMAGINATION", "Louis Vuitton", "Imagination"),
        ("BROOKLYNJAZZ INSPIRED BY MAISON MARGIELA JAZZ CLUB", "Maison Margiela", "Jazz Club"),
    ]

    passed = 0
    failed = 0

    for product_name, expected_brand, expected_fragrance in test_cases:
        result = mapper.extract_from_name(product_name)

        if result:
            brand, fragrance = result
            if brand == expected_brand and fragrance == expected_fragrance:
                print(f"✅ '{product_name}' -> {brand} - {fragrance}")
                passed += 1
            else:
                print(f"❌ '{product_name}' -> Got: {brand} - {fragrance}, Expected: {expected_brand} - {expected_fragrance}")
                failed += 1
        else:
            print(f"❌ '{product_name}' -> No extraction")
            failed += 1

    print(f"\nPassed: {passed}/{len(test_cases)}, Failed: {failed}/{len(test_cases)}")
    return failed == 0


def test_database_methods():
    """Test new database methods"""
    print("\n=== Testing Database Methods ===")

    db = Database()

    # Test data
    test_slug = "test-fragrance-validation"

    try:
        # Clean up any existing test data
        session = db.get_session()
        from models.database import FragranceStock
        session.query(FragranceStock).filter_by(slug=test_slug).delete()
        session.commit()
        session.close()

        # Create test fragrance
        db.save_fragrance_stock({
            'slug': test_slug,
            'name': 'Test Fragrance Inspired by Parfums de Marly Layton',
            'url': 'http://test.com',
            'price': '$30',
            'in_stock': True
        })
        print("✅ Created test fragrance")

        # Test update_fragrance_mapping
        success = db.update_fragrance_mapping(
            slug=test_slug,
            original_brand="Parfums de Marly",
            original_name="Layton",
            parfumo_id="Parfums_de_Marly/Layton"
        )

        if success:
            print("✅ update_fragrance_mapping() works")
        else:
            print("❌ update_fragrance_mapping() failed")
            return False

        # Test update_fragrance_rating
        success = db.update_fragrance_rating(
            slug=test_slug,
            parfumo_id="Parfums_de_Marly/Layton",
            score=8.5,
            votes=1000
        )

        if success:
            print("✅ update_fragrance_rating() works")
        else:
            print("❌ update_fragrance_rating() failed")
            return False

        # Verify data was saved
        fragrances = db.get_all_fragrances()
        test_data = fragrances.get(test_slug)

        if test_data:
            checks = [
                (test_data.get('original_brand') == "Parfums de Marly", "original_brand"),
                (test_data.get('original_name') == "Layton", "original_name"),
                (test_data.get('parfumo_id') == "Parfums_de_Marly/Layton", "parfumo_id"),
                (test_data.get('parfumo_score') == 8.5, "parfumo_score"),
                (test_data.get('parfumo_votes') == 1000, "parfumo_votes"),
            ]

            all_passed = True
            for passed, field in checks:
                if passed:
                    print(f"✅ {field} saved correctly")
                else:
                    print(f"❌ {field} not saved correctly: {test_data.get(field)}")
                    all_passed = False

            if not all_passed:
                return False
        else:
            print("❌ Test fragrance not found in database")
            return False

        # Clean up
        session = db.get_session()
        session.query(FragranceStock).filter_by(slug=test_slug).delete()
        session.commit()
        session.close()
        print("✅ Cleanup successful")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests"""
    print("=" * 60)
    print("Parfumo Matching Improvements - Validation Script")
    print("=" * 60)

    results = []

    results.append(("Database Schema", test_database_schema()))
    results.append(("Multi-word Brand Extraction", test_multi_word_brand_extraction()))
    results.append(("Database Methods", test_database_methods()))

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 All validations passed!")
        return 0
    else:
        print("\n❌ Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
