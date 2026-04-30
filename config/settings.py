"""App configuration constants."""

APP_NAME = "Ashland Hill Media Finance"
APP_SHORT = "AHMF"
APP_PORT = 5010
APP_VERSION = "0.1.0"

# Deal statuses
DEAL_STATUSES = ["pipeline", "active", "closed", "declined"]

# Contact types
CONTACT_TYPES = ["distributor", "producer", "sales_agent", "investor", "legal", "talent", "crew", "other"]

# Project types
PROJECT_TYPES = ["feature_film", "documentary", "series", "short", "animation"]

# Genres
GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "Horror", "Mystery", "Romance",
    "Sci-Fi", "Thriller", "War", "Western",
]

# Territories for sales mapping
TERRITORIES = [
    "Domestic (US/Canada)", "UK", "Germany", "France", "Italy", "Spain",
    "Scandinavia", "Benelux", "Australia/NZ", "Japan", "South Korea",
    "China", "Latin America", "Middle East", "Africa", "Eastern Europe",
    "India", "Southeast Asia", "Rest of World",
]

# Currencies
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"]

# Risk scoring dimensions
RISK_DIMENSIONS = [
    "Script Complexity", "Budget Feasibility", "Schedule Risk",
    "Jurisdictional Risk", "Crew/Talent Risk", "Completion Risk",
]
RISK_TIERS = {"low": (0, 30), "moderate": (31, 55), "elevated": (56, 75), "high": (76, 100)}

# VFX levels for risk/budget
VFX_LEVELS = ["None", "Light", "Moderate", "Heavy", "VFX-Driven"]

# Cast tiers for budgeting
CAST_TIERS = ["Unknown", "Emerging", "Mid-Level", "A-List", "Marquee"]

# Budget categories (industry-standard line items)
BUDGET_CATEGORIES = [
    "Story & Rights", "Producer", "Director", "Cast",
    "Extras", "Production Staff", "Art Department", "Set Construction",
    "Props", "Wardrobe", "Makeup & Hair", "Grip & Electrical",
    "Camera", "Sound", "Transportation", "Locations", "Catering",
    "Visual Effects", "Music", "Post-Production Picture",
    "Post-Production Sound", "Insurance", "Legal", "Financing Costs",
    "Publicity", "Contingency", "Overhead/Fee",
]

# Budget category groupings
BUDGET_GROUPS = {
    "Above-the-Line (ATL)": ["Story & Rights", "Producer", "Director", "Cast"],
    "Below-the-Line (BTL)": [
        "Extras", "Production Staff", "Art Department", "Set Construction",
        "Props", "Wardrobe", "Makeup & Hair", "Grip & Electrical",
        "Camera", "Sound", "Transportation", "Locations", "Catering",
    ],
    "Post-Production": ["Visual Effects", "Music", "Post-Production Picture", "Post-Production Sound"],
    "Other": ["Insurance", "Legal", "Financing Costs", "Publicity", "Contingency", "Overhead/Fee"],
}

# Closing checklist template
CLOSING_CHECKLIST_TEMPLATE = [
    ("Legal", "Fully executed loan agreement"),
    ("Legal", "Security agreement / collateral pledge"),
    ("Legal", "Completion guarantee"),
    ("Legal", "Inter-party agreement"),
    ("Legal", "Producer's legal opinion letter"),
    ("Insurance", "E&O insurance certificate"),
    ("Insurance", "Production insurance binder"),
    ("Insurance", "Completion bond"),
    ("Financial", "Chain of title documentation"),
    ("Financial", "Approved budget and cashflow schedule"),
    ("Financial", "Lab access letter"),
    ("Financial", "Collection account management agreement (CAMA)"),
    ("Distribution", "Executed distribution agreement(s)"),
    ("Distribution", "Delivery schedule"),
    ("Distribution", "Sales estimates / MG commitments"),
    ("Tax Incentives", "Tax incentive application filed"),
    ("Tax Incentives", "Auditor opinion letter"),
    ("Compliance", "KYC / AML documentation"),
    ("Compliance", "OFAC screening completed"),
    ("Compliance", "Board / investment committee approval"),
]
