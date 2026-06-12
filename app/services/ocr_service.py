"""
OCR Service — temporary mock for development/testing.
Replace with real Google Vision API when credentials are available.
"""

def extract_text(image_path: str) -> str:
    """Returns mock nutrition label text for testing purposes."""
    return """Serving Size 1 Scoop (30g)
Calories 120
Protein 24g
Total Carbohydrates 3g
Total Fat 1.5g
Sugar 1g
Fiber 2g
Sodium 150mg
Ingredients: Whey Protein Isolate, Natural Flavors, Soy Lecithin, Salt, Sucralose.
Contains Milk and Soy."""
