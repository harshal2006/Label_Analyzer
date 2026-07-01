#!/usr/bin/env python3
"""
Test script for the deterministic health score calculator.

Runs 3 mock product profiles and prints their scores to verify
the algorithm produces a realistic spread (2-3, 5-6, 8-9).

Usage:
    python -m app.services.test_health_score
"""

import sys
import os

# Ensure the project root is on sys.path so `app.` imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.services.health_score import calculate_health_score


def main():
    print("=" * 70)
    print("HEALTH SCORE ALGORITHM — TEST RESULTS")
    print("=" * 70)

    # ── Product 1: Clean whey protein (expected: 8-9) ──
    product_1_nutrients = {
        "Calories":         "120 kcal",
        "Protein":          "24 g",       # 48% DV
        "Total Fat":        "1.5 g",      # 1.9% DV
        "Saturated Fat":    "0.5 g",      # 2.5% DV
        "Trans Fat":        "0 g",        # 0% DV
        "Total Carbohydrate": "3 g",      # 1.1% DV
        "Total Sugars":     "1 g",        # 2% DV
        "Added Sugars":     "0 g",        # 0% DV
        "Sodium":           "50 mg",      # 2.2% DV
        "Calcium":          "120 mg",     # 9.2% DV
        "Iron":             "0.5 mg",     # 2.8% DV
        "Potassium":        "160 mg",     # 3.4% DV
    }
    product_1_ingredients = [
        "Whey Protein Concentrate",
        "Whey Protein Isolate",
        "Cocoa Powder",
        "Natural Flavors",
        "Lecithin",
        "Stevia",
    ]

    score_1, reasoning_1 = calculate_health_score(product_1_nutrients, product_1_ingredients)
    print(f"\n{'─' * 70}")
    print(f"Product 1: CLEAN WHEY PROTEIN")
    print(f"  Score:     {score_1}/10")
    print(f"  Reasoning: {reasoning_1}")

    # ── Product 2: Sugary energy drink (expected: 2-3) ──
    product_2_nutrients = {
        "Calories":         "230 kcal",
        "Protein":          "0 g",        # 0% DV
        "Total Fat":        "0 g",        # 0% DV
        "Saturated Fat":    "0 g",        # 0% DV
        "Trans Fat":        "0 g",        # 0% DV
        "Total Carbohydrate": "58 g",     # 21% DV
        "Total Sugars":     "54 g",       # 108% DV
        "Added Sugars":     "54 g",       # 108% DV
        "Sodium":           "75 mg",      # 3.3% DV
        "Vitamin B3":       "20 mg",      # 125% DV
        "Vitamin B6":       "2 mg",       # 118% DV
        "Vitamin B12":      "6 mcg",      # 250% DV
    }
    product_2_ingredients = [
        "Carbonated Water",
        "High Fructose Corn Syrup",
        "Citric Acid",
        "Sodium Benzoate",
        "Potassium Sorbate",
        "Yellow 5",
        "Red 40",
        "Artificial Flavor",
        "Sucralose",
        "Caffeine",
        "Taurine",
    ]

    score_2, reasoning_2 = calculate_health_score(product_2_nutrients, product_2_ingredients)
    print(f"\n{'─' * 70}")
    print(f"Product 2: SUGARY ENERGY DRINK")
    print(f"  Score:     {score_2}/10")
    print(f"  Reasoning: {reasoning_2}")

    # ── Product 3: Average granola bar (expected: 5-6) ──
    product_3_nutrients = {
        "Calories":         "190 kcal",
        "Protein":          "6 g",        # 12% DV
        "Total Fat":        "7 g",        # 9% DV
        "Saturated Fat":    "2.5 g",      # 12.5% DV
        "Trans Fat":        "0 g",        # 0% DV
        "Total Carbohydrate": "28 g",     # 10.2% DV
        "Dietary Fiber":    "3 g",        # 10.7% DV
        "Total Sugars":     "12 g",       # 24% DV
        "Added Sugars":     "8 g",        # 16% DV
        "Sodium":           "150 mg",     # 6.5% DV
        "Iron":             "2 mg",       # 11.1% DV
        "Calcium":          "40 mg",      # 3.1% DV
    }
    product_3_ingredients = [
        "Rolled Oats",
        "Brown Rice Syrup",
        "Semi-Sweet Chocolate Chips",
        "Almonds",
        "Peanut Butter",
        "Honey",
        "Coconut Oil",
        "Sea Salt",
        "Natural Flavors",
        "Soy Lecithin",
    ]

    score_3, reasoning_3 = calculate_health_score(product_3_nutrients, product_3_ingredients)
    print(f"\n{'─' * 70}")
    print(f"Product 3: AVERAGE GRANOLA BAR")
    print(f"  Score:     {score_3}/10")
    print(f"  Reasoning: {reasoning_3}")

    # ── Summary ──
    print(f"\n{'═' * 70}")
    print("SUMMARY")
    print(f"  Clean Whey Protein:   {score_1}/10  (expected: 8-9)")
    print(f"  Sugary Energy Drink:  {score_2}/10  (expected: 2-3)")
    print(f"  Average Granola Bar:  {score_3}/10  (expected: 5-6)")
    print(f"{'═' * 70}")


if __name__ == "__main__":
    main()
