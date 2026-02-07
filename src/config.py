from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Orders
ORDERS_FILE = DATA_DIR / "orders.json"

# Complaints
COMPLAINTS_FILE = DATA_DIR / "complaints.json"
COMPLAINT_IMAGES_DIR = DATA_DIR / "complaints_images"

# Internal statuses (DO NOT change these values)
ORDER_STATUSES = {
    "received",
    "preparing",
    "out_for_delivery",
    "delivered",
    "cancelled"
}

# Supported languages
LANGUAGES = {"ar", "en"}

# Status labels per language (for display only)
STATUS_LABELS = {
    "received": {"ar": "تم استلام الطلب", "en": "Order received"},
    "preparing": {"ar": "قيد التحضير", "en": "Preparing order"},
    "out_for_delivery": {"ar": "قيد التوصيل", "en": "Out for delivery"},
    "delivered": {"ar": "تم التسليم", "en": "Delivered"},
    "cancelled": {"ar": "ملغي", "en": "Cancelled"},
}

# ============================================================
# Demo Auth Users (Change later to env/DB)
# ============================================================
# Username:Password
ADMIN_USERS = {
    "admin": "admin123",
    "ali": "ali123",
}

AGENT_USERS = {
    "agent": "agent123",
    "rahaf": "rahaf123",
}
