import sys
from io import BytesIO
from app.services.pdf_service import generate_report_pdf
from app.services.nutrition_analysis import detect_allergens

def main():
    product_info = {"upload_id": 1000, "image_path": "uploads/safe_product.jpg"}
    nutrients = {"Protein": "0 g", "Total Fat": "0 g", "Sodium": "5 mg"}
    primary_goal = "A safe drink."
    insights = {}
    dv_flags = {}
    
    ingredient_text = "Ingredients: Water, natural flavor."
    allergens = detect_allergens(ingredient_text)
    print("Detected Allergens:", allergens)
    
    macro_split = {"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0}

    buf = generate_report_pdf(
        product_info=product_info,
        nutrients=nutrients,
        primary_goal=primary_goal,
        insights=insights,
        dv_flags=dv_flags,
        allergens=allergens,
        macro_split=macro_split,
    )
    
    with open("test_report_safe.pdf", "wb") as f:
        f.write(buf.getvalue())
    print("PDF generated successfully: test_report_safe.pdf")

if __name__ == "__main__":
    main()
