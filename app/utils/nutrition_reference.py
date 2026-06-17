"""
Nutrition reference data — FDA Daily Values and common allergens.

Used by the pure analysis functions in ``nutrition_analysis.py`` to compute
%DV flags and detect allergens without any external API calls.
"""

# ---------------------------------------------------------------------------
# FDA Daily Values (2020+ reference amounts)
#
# Keys MUST match the nutrient names produced by ocr_service.KNOWN_NUTRIENTS.
# Where the parser can emit multiple synonyms (e.g. "Total Carbohydrate" and
# "Carbohydrate"), we include all of them so look-ups always succeed.
# Values are in the unit that the parser typically produces.
# ---------------------------------------------------------------------------
DAILY_VALUES: dict[str, dict] = {
    # ── Macronutrients ──
    "Calories":             {"value": 2000, "unit": "kcal"},
    "Energy":               {"value": 2000, "unit": "kcal"},
    "Total Fat":            {"value": 78,   "unit": "g"},
    "Fat":                  {"value": 78,   "unit": "g"},
    "Saturated Fat":        {"value": 20,   "unit": "g"},
    "Trans Fat":            {"value": 2,    "unit": "g"},     # no official DV; 2 g ceiling used
    "Cholesterol":          {"value": 300,  "unit": "mg"},
    "Sodium":               {"value": 2300, "unit": "mg"},
    "Total Carbohydrate":   {"value": 275,  "unit": "g"},
    "Total Carbohydrates":  {"value": 275,  "unit": "g"},
    "Carbohydrate":         {"value": 275,  "unit": "g"},
    "Carbohydrates":        {"value": 275,  "unit": "g"},
    "Dietary Fiber":        {"value": 28,   "unit": "g"},
    "Dietary Fibre":        {"value": 28,   "unit": "g"},
    "Fiber":                {"value": 28,   "unit": "g"},
    "Fibre":                {"value": 28,   "unit": "g"},
    "Total Sugars":         {"value": 50,   "unit": "g"},
    "Sugar":                {"value": 50,   "unit": "g"},
    "Sugars":               {"value": 50,   "unit": "g"},
    "Added Sugars":         {"value": 50,   "unit": "g"},
    "Added Sugar":          {"value": 50,   "unit": "g"},
    "Protein":              {"value": 50,   "unit": "g"},

    # ── Vitamins ──
    "Vitamin A":            {"value": 900,  "unit": "mcg"},
    "Vitamin C":            {"value": 90,   "unit": "mg"},
    "Vitamin D":            {"value": 20,   "unit": "mcg"},
    "Vitamin E":            {"value": 15,   "unit": "mg"},
    "Vitamin K":            {"value": 120,  "unit": "mcg"},
    "Vitamin B1":           {"value": 1.2,  "unit": "mg"},
    "Thiamine":             {"value": 1.2,  "unit": "mg"},
    "Vitamin B2":           {"value": 1.3,  "unit": "mg"},
    "Riboflavin":           {"value": 1.3,  "unit": "mg"},
    "Vitamin B3":           {"value": 16,   "unit": "mg"},
    "Niacin":               {"value": 16,   "unit": "mg"},
    "Vitamin B5":           {"value": 5,    "unit": "mg"},
    "Pantothenic Acid":     {"value": 5,    "unit": "mg"},
    "Vitamin B6":           {"value": 1.7,  "unit": "mg"},
    "Vitamin B12":          {"value": 2.4,  "unit": "mcg"},
    "Biotin":               {"value": 30,   "unit": "mcg"},
    "Folate":               {"value": 400,  "unit": "mcg"},
    "Folic Acid":           {"value": 400,  "unit": "mcg"},

    # ── Minerals ──
    "Calcium":              {"value": 1300, "unit": "mg"},
    "Iron":                 {"value": 18,   "unit": "mg"},
    "Potassium":            {"value": 4700, "unit": "mg"},
    "Phosphorus":           {"value": 1250, "unit": "mg"},
    "Magnesium":            {"value": 420,  "unit": "mg"},
    "Zinc":                 {"value": 11,   "unit": "mg"},
    "Selenium":             {"value": 55,   "unit": "mcg"},
    "Copper":               {"value": 0.9,  "unit": "mg"},
    "Manganese":            {"value": 2.3,  "unit": "mg"},
    "Chromium":             {"value": 35,   "unit": "mcg"},
    "Iodine":               {"value": 150,  "unit": "mcg"},
    "Chloride":             {"value": 2300, "unit": "mg"},
}


# ---------------------------------------------------------------------------
# Common allergens (FDA "Big 9")
#
# Each entry maps a display-friendly allergen name to a list of lowercase
# keywords/synonyms to search for in OCR / ingredient text.
# ---------------------------------------------------------------------------
COMMON_ALLERGENS: list[dict[str, list[str]]] = [
    {"name": "Milk",       "keywords": ["milk", "dairy", "lactose", "casein", "whey", "cream", "butter", "ghee", "curd"]},
    {"name": "Eggs",       "keywords": ["egg", "eggs", "albumin", "ovalbumin", "lysozyme"]},
    {"name": "Fish",       "keywords": ["fish", "cod", "salmon", "tuna", "anchovy", "sardine", "bass", "tilapia"]},
    {"name": "Shellfish",  "keywords": ["shellfish", "shrimp", "crab", "lobster", "prawn", "crayfish", "crawfish"]},
    {"name": "Tree Nuts",  "keywords": ["tree nut", "tree nuts", "almond", "cashew", "walnut", "pecan", "pistachio", "macadamia", "hazelnut", "brazil nut"]},
    {"name": "Peanuts",    "keywords": ["peanut", "peanuts", "groundnut", "groundnuts", "arachis"]},
    {"name": "Wheat",      "keywords": ["wheat", "gluten", "semolina", "spelt", "durum", "farina", "kamut"]},
    {"name": "Soy",        "keywords": ["soy", "soya", "soybean", "soybeans", "edamame", "tofu", "soy lecithin"]},
    {"name": "Sesame",     "keywords": ["sesame", "tahini", "sesame seed", "sesame oil"]},
]
