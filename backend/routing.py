"""
ONOCP Smart Routing Engine
Detects complaint category from text and maps it to the right government
department + SLA deadline. Keyword-based for MVP — swap detect_category()
with a trained ML/embeddings classifier later without touching the rest
of the app.
"""

CATEGORY_CONFIG = {
    "Water Supply": {
        "department": "Municipal Water Board",
        "sla_days": 3,
        "color": "#2E86AB",
        "keywords": ["water", "pipeline", "leak", "supply", "tanker", "tap", "borewell", "pani"],
    },
    "Electricity": {
        "department": "State Electricity Board",
        "sla_days": 2,
        "color": "#C89B3C",
        "keywords": ["power", "electricity", "transformer", "wire", "outage", "streetlight", "current", "bijli"],
    },
    "Roads & Infrastructure": {
        "department": "Public Works Department (PWD)",
        "sla_days": 7,
        "color": "#6B4226",
        "keywords": ["road", "pothole", "bridge", "footpath", "construction", "gadha", "sadak", "divider"],
    },
    "Sanitation & Garbage": {
        "department": "Municipal Sanitation Department",
        "sla_days": 3,
        "color": "#4C7A3D",
        "keywords": ["garbage", "trash", "sewage", "drain", "cleanliness", "waste", "kachra", "gutter", "smell"],
    },
    "Health Services": {
        "department": "Department of Public Health",
        "sla_days": 2,
        "color": "#B23A2E",
        "keywords": ["hospital", "doctor", "medicine", "clinic", "health", "ambulance", "dawai"],
    },
    "Police & Safety": {
        "department": "Local Police Station",
        "sla_days": 1,
        "color": "#0B2545",
        "keywords": ["theft", "crime", "safety", "police", "harassment", "accident", "chori", "unsafe"],
    },
    "Public Transport": {
        "department": "Regional Transport Authority",
        "sla_days": 5,
        "color": "#7A4E9E",
        "keywords": ["bus", "train", "auto", "transport", "metro", "rickshaw", "conductor"],
    },
    "General Administration": {
        "department": "General Administration Cell",
        "sla_days": 5,
        "color": "#5C5C5C",
        "keywords": [],
    },
}

DEFAULT_CATEGORY = "General Administration"


def detect_category(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    best_category = DEFAULT_CATEGORY
    best_score = 0
    for category, cfg in CATEGORY_CONFIG.items():
        score = sum(1 for kw in cfg["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


def get_department(category: str) -> str:
    return CATEGORY_CONFIG.get(category, CATEGORY_CONFIG[DEFAULT_CATEGORY])["department"]


def get_sla_days(category: str) -> int:
    return CATEGORY_CONFIG.get(category, CATEGORY_CONFIG[DEFAULT_CATEGORY])["sla_days"]


def get_color(category: str) -> str:
    return CATEGORY_CONFIG.get(category, CATEGORY_CONFIG[DEFAULT_CATEGORY])["color"]


def all_categories():
    return list(CATEGORY_CONFIG.keys())
