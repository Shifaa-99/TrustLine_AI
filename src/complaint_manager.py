import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import uuid

from src.config import COMPLAINTS_FILE


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_parent():
    COMPLAINTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_raw() -> Any:
    if not COMPLAINTS_FILE.exists():
        return []
    try:
        with open(COMPLAINTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # مهم: لا تبلع الخطأ بصمت
        print("ERROR: Failed to read complaints file:", COMPLAINTS_FILE, "err:", repr(e))
        return []


def _normalize_to_list(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [v for v in raw.values() if isinstance(v, dict)]
    return []


def _atomic_write_json(path: Path, data: Any) -> None:
    _ensure_parent()
    tmp = path.with_suffix(path.suffix + ".tmp")

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())

    # replace atomic على أغلب الأنظمة
    tmp.replace(path)


def _save_list(rows: List[Dict[str, Any]]) -> None:
    _atomic_write_json(COMPLAINTS_FILE, rows)


def list_complaints() -> List[Dict[str, Any]]:
    raw = _load_raw()
    return _normalize_to_list(raw)


def get_complaint(complaint_id: str) -> Optional[Dict[str, Any]]:
    rows = list_complaints()
    return next((c for c in rows if c.get("complaint_id") == complaint_id), None)


def create_complaint_record(
    order_id: str,
    customer_name: str,
    phone: str,
    message: str,
    image_paths: List[str],
    category: str = "other",
) -> Dict[str, Any]:
    rows = list_complaints()

    # تجنب تصادم بنفس الثانية
    complaint_id = f"CMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    rec = {
        "complaint_id": complaint_id,
        "order_id": order_id,
        "customer_name": customer_name,
        "phone": phone,
        "message": message,
        "category": category,
        "status": "new",
        "images": image_paths or [],
        "internal_note": "",
        "created_at": _now_iso(),
        "updated_at": None,
    }

    print("DEBUG: create_complaint_record CALLED", order_id, category)
    print("DEBUG: COMPLAINTS_FILE =", COMPLAINTS_FILE)

    rows.append(rec)
    _save_list(rows)
    return rec


def update_complaint(complaint_id: str, patch: Dict[str, Any]) -> bool:
    rows = list_complaints()
    for c in rows:
        if c.get("complaint_id") == complaint_id:
            c.update(patch or {})
            c["updated_at"] = _now_iso()
            _save_list(rows)
            return True
    return False
