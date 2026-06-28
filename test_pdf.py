import sys
from io import BytesIO
from app.services.pdf_service import generate_report_pdf
from app.services.nutrition_analysis import detect_allergens

def main():
    product_info = {"upload_id": 999, "image_path": "uploads/test_product.jpg"}
    nutrients = {"Protein": "24 g", "Total Fat": "2 g", "Sodium": "150 mg"}
    primary_goal = "This is a test primary goal summarizing the product's high protein content for muscle recovery."
    insights = {
        "Protein": {"source": "Dairy (Whey/Casein)", "usage": "Muscle recovery and building blocks."},
        "Total Fat": {"source": "Dairy fat", "usage": "Texture and flavor."},
        "Sodium": {"source": "Added salt", "usage": "Electrolyte balance."}
    }
    dv_flags = {
        "Protein": {"percent_dv": 48.0, "flag": "High"},
        "Total Fat": {"percent_dv": 2.5, "flag": "Low"},
        "Sodium": {"percent_dv": 6.5, "flag": "Moderate"}
    }
    
    # Test allergen grouping: whey and casein should group under Milk.
    ingredient_text = "Ingredients: Whey protein concentrate, calcium caseinate, cocoa powder, soy lecithin, sucralose."
    allergens = detect_allergens(ingredient_text)
    print("Detected Allergens:", allergens)
    
    macro_split = {"protein_pct": 84.2, "carbs_pct": 0.0, "fat_pct": 15.8}

    buf = generate_report_pdf(
        product_info=product_info,
        nutrients=nutrients,
        primary_goal=primary_goal,
        insights=insights,
        dv_flags=dv_flags,
        allergens=allergens,
        macro_split=macro_split,
    )
    
    with open("test_report.pdf", "wb") as f:
        f.write(buf.getvalue())
    print("PDF generated successfully: test_report.pdf")

if __name__ == "__main__":
    main()
