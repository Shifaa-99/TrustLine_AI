from pathlib import Path

from pathlib import Path

# project root = folder اللي فوق src
ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"
RAG_INDEX_DIR = ROOT_DIR / "rag_index"

ORDERS_FILE = DATA_DIR / "orders.json"
COMPLAINTS_FILE = DATA_DIR / "complaints.json"
KNOWLEDGE_FILE = DATA_DIR / "knowledge_base.txt"
COMPLAINTS_IMAGES_DIR = DATA_DIR / "complaints_images"


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
