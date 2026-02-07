import json
from datetime import datetime
from typing import Any, Dict, List
import re

from src.config import ORDERS_FILE, ORDER_STATUSES, STATUS_LABELS

# ===============================
# Internal helpers
# ===============================

PAYMENT_METHODS = ["cash", "card", "online", "wallet"]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_orders_parent():
    ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_orders() -> dict:
    """
    Safe load:
    - If file doesn't exist -> {}
    - If JSON is corrupted/empty -> {}
    """
    if not ORDERS_FILE.exists():
        return {}

    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        # corrupted json, empty file, etc.
        return {}


def _save_orders(data: dict):
    _ensure_orders_parent()
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_status(input_status: str) -> str:
    if not input_status:
        raise ValueError("Status is required")

    s = input_status.strip().lower()

    for key, labels in STATUS_LABELS.items():
        if s == key:
            return key
        if s in [v.lower() for v in labels.values()]:
            return key

    raise ValueError("Unknown order status")


def format_status(status_key: str, lang: str = "en") -> str:
    return STATUS_LABELS.get(status_key, {}).get(lang, status_key)


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""

    digits = re.sub(r"\D", "", str(phone))  # keep digits only

    # Jordan country code 962 -> convert to local starting 0
    if digits.startswith("962"):
        digits = "0" + digits[3:]

    return digits


def normalize_payment_method(pm: str) -> str:
    if not pm:
        return "cash"
    pm = str(pm).strip().lower()
    # إذا بدك تمنع أي قيمة خارج القائمة: خليه يرفع خطأ بدل ما يرجع cash
    if pm not in PAYMENT_METHODS:
        return "cash"
    return pm


def _clean_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


# ===============================
# CRUD operations
# ===============================

def create_order(
    order_id: str,
    customer_name: str,
    phone: str,
    address: str,
    items: list,
    payment_method: str = "cash"
):
    orders = _load_orders()

    order_id = _clean_str(order_id)
    if not order_id:
        raise ValueError("Order ID is required.")

    if order_id in orders:
        raise ValueError(f"Order {order_id} already exists.")

    customer_name = _clean_str(customer_name)
    phone = normalize_phone(_clean_str(phone))
    address = _clean_str(address)
    payment_method = normalize_payment_method(payment_method)

    if items is None:
        items = []

    orders[order_id] = {
        "customer_name": customer_name,
        "phone": phone,
        "delivery_address": address,
        "items": items,
        "payment_method": payment_method,
        "status": "received",
        "created_at": _now_iso(),
        "last_updated": _now_iso()
    }

    _save_orders(orders)


def update_order_status(order_id: str, new_status: str):
    orders = _load_orders()

    order_id = _clean_str(order_id)
    if order_id not in orders:
        raise ValueError("Order not found.")

    status_key = normalize_status(new_status)
    if status_key not in ORDER_STATUSES:
        raise ValueError("Invalid status.")

    orders[order_id]["status"] = status_key
    orders[order_id]["last_updated"] = _now_iso()

    _save_orders(orders)


def update_order(order_id: str, patch: dict):
    """
    Update order fields safely.
    Allowed keys:
    - customer_name
    - phone
    - delivery_address
    - items
    - status
    - payment_method
    """
    orders = _load_orders()

    order_id = _clean_str(order_id)
    if order_id not in orders:
        raise ValueError("Order not found.")

    allowed = {"customer_name", "phone", "delivery_address", "items", "status", "payment_method"}
    patch = patch or {}

    clean: Dict[str, Any] = {k: v for k, v in patch.items() if k in allowed}

    if "customer_name" in clean:
        clean["customer_name"] = _clean_str(clean["customer_name"])

    if "phone" in clean:
        clean["phone"] = normalize_phone(_clean_str(clean["phone"]))

    if "delivery_address" in clean:
        clean["delivery_address"] = _clean_str(clean["delivery_address"])

    if "payment_method" in clean:
        clean["payment_method"] = normalize_payment_method(clean["payment_method"])

    if "status" in clean:
        clean["status"] = normalize_status(clean["status"])
        if clean["status"] not in ORDER_STATUSES:
            raise ValueError("Invalid status.")

    # items: keep as-is (list[str] or list[dict]) but ensure list type
    if "items" in clean and clean["items"] is None:
        clean["items"] = []

    orders[order_id].update(clean)
    orders[order_id]["last_updated"] = _now_iso()
    _save_orders(orders)


def get_order(order_id: str, lang: str = "en") -> dict:
    orders = _load_orders()

    order_id = _clean_str(order_id)
    if order_id not in orders:
        raise ValueError("Order not found.")

    order = orders[order_id].copy()
    order["status_label"] = format_status(order.get("status", ""), lang)

    return order


def list_orders(lang: str = "en") -> dict:
    orders = _load_orders()
    output = {}

    for oid, o in orders.items():
        oo = dict(o)
        oo["status_label"] = format_status(o.get("status", ""), lang)
        output[oid] = oo

    return output


def find_orders_by_phone(phone: str) -> list:
    phone = normalize_phone(phone)
    orders = _load_orders()
    matches = []

    for order_id, order in orders.items():
        stored_phone = normalize_phone(order.get("phone", ""))
        if stored_phone == phone:
            matches.append(order_id)

    return matches
