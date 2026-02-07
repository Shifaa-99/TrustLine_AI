import streamlit as st
import pandas as pd
from pathlib import Path

from src.auth import require_role, logout
from src.ui import app_header, sidebar_shell
from src.complaint_manager import list_complaints, get_complaint, update_complaint
from src.config import ORDER_STATUSES
from src.order_manager import (
    list_orders,
    create_order,
    update_order_status,
    get_order,
    update_order,
)

# =========================
# Guard
# =========================
require_role("admin")

auth = st.session_state.auth
app_header("Admin Dashboard", "Orders • Complaints • SLA • Assignment")
sidebar_shell("Admin Panel", auth["username"], auth["role"])

if st.sidebar.button("Logout"):
    logout()
    st.rerun()

# =========================
# STATUS OPTIONS
# =========================
PREFERRED_STATUS_ORDER = ["received", "preparing", "out_for_delivery", "delivered", "cancelled"]
STATUS_OPTIONS = [s for s in PREFERRED_STATUS_ORDER if s in ORDER_STATUSES] + \
                 sorted([s for s in ORDER_STATUSES if s not in PREFERRED_STATUS_ORDER])

def status_index(current: str) -> int:
    return STATUS_OPTIONS.index(current) if current in STATUS_OPTIONS else 0

# =========================
# Payment method options (FIX: define globally)
# =========================
PM_OPTIONS = ["cash", "card", "online", "wallet", "other"]

# =========================
# Helpers for items
# =========================
def items_to_df(items):
    rows = []
    if not items:
        return pd.DataFrame(rows, columns=["name", "quantity", "unit_price", "note"])

    for it in items:
        if isinstance(it, dict):
            rows.append({
                "name": it.get("name", ""),
                "quantity": it.get("quantity", 1),
                "unit_price": it.get("unit_price", 0),
                "note": it.get("note", ""),
            })
        else:
            rows.append({"name": str(it), "quantity": 1, "unit_price": 0, "note": ""})

    return pd.DataFrame(rows, columns=["name", "quantity", "unit_price", "note"])


def df_to_items(df):
    items = []
    if df is None or df.empty:
        return items

    for _, r in df.iterrows():
        name = str(r.get("name", "")).strip()
        if not name:
            continue

        try:
            qty = int(r.get("quantity", 1))
        except Exception:
            qty = 1

        try:
            price = float(r.get("unit_price", 0))
        except Exception:
            price = 0.0

        items.append({
            "name": name,
            "quantity": max(qty, 1),
            "unit_price": max(price, 0),
            "note": str(r.get("note", "")).strip(),
        })

    return items


def calc_total(items):
    total = 0.0
    for it in items or []:
        total += (it.get("quantity", 1) or 1) * (it.get("unit_price", 0) or 0)
    return total


# =========================
# Load data
# =========================
orders = list_orders(lang="en") or {}
complaints = list_complaints() or []

# =========================
# KPIs
# =========================
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Orders", len(orders))
k2.metric("Delivered", sum(1 for o in orders.values() if o.get("status") == "delivered"))
k3.metric("Open Complaints", sum(1 for c in complaints if c.get("status") in ["new", "in_progress"]))
k4.metric("Resolved", sum(1 for c in complaints if c.get("status") == "resolved"))

st.divider()
tab1, tab2, tab3 = st.tabs(["📦 Orders", "🧾 Complaints", "⚙️ Settings"])

# =========================
# TAB 1: Orders
# =========================
with tab1:
    st.markdown("### Orders")

    # -------- Create Order --------
    with st.expander("➕ Create New Order"):
        with st.form("create_order_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            order_id = c1.text_input("Order ID")
            customer_name = c2.text_input("Customer Name")

            c3, c4 = st.columns(2)
            phone = c3.text_input("Phone")
            address = c4.text_input("Address / Location")

            pm_choice = st.selectbox("Payment Method", PM_OPTIONS, key="pm_create")
            pm_custom = ""
            if pm_choice == "other":
                pm_custom = st.text_input("Other payment method", key="pm_create_other")

            payment_method = pm_custom.strip().lower() if pm_choice == "other" else pm_choice

            sample_df = pd.DataFrame([
                {"name": "Laptop Bag", "quantity": 1, "unit_price": 12.5, "note": ""},
                {"name": "Charger", "quantity": 2, "unit_price": 8.0, "note": "USB-C"},
            ])

            items_df = st.data_editor(sample_df, num_rows="dynamic", use_container_width=True, key="items_create")

            if st.form_submit_button("Create Order", type="primary"):
                try:
                    create_order(
                        order_id=order_id.strip(),
                        customer_name=customer_name.strip(),
                        phone=phone.strip(),
                        address=address.strip(),
                        items=df_to_items(items_df),
                        payment_method=payment_method
                    )
                    st.success("✅ Order created")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # -------- Edit Order --------
    if orders:
        st.markdown("#### ✏️ Edit Order")
        oid = st.selectbox("Select Order", sorted(orders.keys()), key="edit_order_select")

        try:
            o = get_order(oid, lang="en")
        except Exception as e:
            st.error(str(e))
            o = None

        if o:
            # Quick Status Update (only place)
            st.markdown("**Quick Status Update**")
            c1, c2 = st.columns([3, 1])
            new_status = c1.selectbox("Status", STATUS_OPTIONS, index=status_index(o.get("status", "received")), key="status_quick")
            if c2.button("Update Status", key="btn_update_status"):
                try:
                    update_order_status(oid, new_status)
                    st.success("Status updated")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            st.divider()

            # Full Edit (NO status here)
            c3, c4 = st.columns(2)
            new_customer = c3.text_input("Customer Name", o.get("customer_name", ""), key="edit_customer")
            new_phone = c4.text_input("Phone", o.get("phone", ""), key="edit_phone")

            new_address = st.text_input("Address", o.get("delivery_address", ""), key="edit_address")

            pm_current = (o.get("payment_method") or "cash").strip().lower()
            pm_index = PM_OPTIONS.index(pm_current) if pm_current in PM_OPTIONS else PM_OPTIONS.index("other")

            pm_choice = st.selectbox("Payment Method", PM_OPTIONS, index=pm_index, key="pm_edit")
            pm_custom = ""
            if pm_choice == "other":
                pm_custom = st.text_input("Other payment method", value=pm_current, key="pm_edit_other")

            payment_method_edit = pm_custom.strip().lower() if pm_choice == "other" else pm_choice

            items_df = items_to_df(o.get("items"))
            edited_items_df = st.data_editor(items_df, num_rows="dynamic", use_container_width=True, key="items_edit")

            st.info(f"Estimated total: {calc_total(df_to_items(edited_items_df)):.2f}")

            if st.button("Save Changes", type="primary", key="btn_save_order"):
                try:
                    update_order(oid, {
                        "customer_name": new_customer,
                        "phone": new_phone,
                        "delivery_address": new_address,
                        "items": df_to_items(edited_items_df),
                        "payment_method": payment_method_edit
                    })
                    st.success("Order updated")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # Orders Table
    st.markdown("#### 📄 Orders List")
    rows = []
    for oid, o in orders.items():
        rows.append({
            "order_id": oid,
            "customer": o.get("customer_name"),
            "phone": o.get("phone"),
            "payment": o.get("payment_method"),
            "status": o.get("status"),
            "total": calc_total(o.get("items")),
            "updated": o.get("last_updated")
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

# =========================
# TAB 2: Complaints
# =========================
with tab2:
    st.markdown("### Complaints")

    complaint_statuses = ["new", "in_progress", "resolved"]

    if not complaints:
        st.info("No complaints yet.")
    else:
        # ----------- Table (summary) -----------
        st.markdown("#### 📄 Complaints List")

        rows = []
        for c in complaints:
            rows.append({
                "complaint_id": c.get("complaint_id"),
                "order_id": c.get("order_id"),
                "category": c.get("category"),
                "status": c.get("status"),
                "assigned_to": c.get("assigned_to"),
                "created_at": c.get("created_at"),
                "updated_at": c.get("updated_at"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.divider()

        # ----------- Details panel -----------
        st.markdown("#### 🔎 Complaint Details")

        complaint_ids = sorted([c.get("complaint_id") for c in complaints if c.get("complaint_id")])
        selected_cid = st.selectbox("Select Complaint", complaint_ids, key="complaint_select")

        cobj = get_complaint(selected_cid)
        if not cobj:
            st.error("Complaint not found.")
        else:
            # ===== Full details =====
            c1, c2 = st.columns(2)
            c1.text_input("Complaint ID", value=str(cobj.get("complaint_id", "")), disabled=True)
            c2.text_input("Order ID", value=str(cobj.get("order_id", "")), disabled=True)

            c3, c4 = st.columns(2)
            c3.text_input("Customer Name", value=str(cobj.get("customer_name", "")), disabled=True)
            c4.text_input("Phone", value=str(cobj.get("phone", "")), disabled=True)

            c5, c6 = st.columns(2)
            category = c5.text_input("Category", value=str(cobj.get("category", "other") or "other"))
            status = c6.selectbox(
                "Status",
                options=complaint_statuses,
                index=complaint_statuses.index(cobj.get("status", "new")) if cobj.get("status", "new") in complaint_statuses else 0
            )

            assigned_to = st.text_input("Assigned To (optional)", value=str(cobj.get("assigned_to", "") or ""))
            internal_note = st.text_area("Internal Note", value=str(cobj.get("internal_note", "") or ""), height=120)

            st.markdown("##### Customer Message")
            st.text_area("", value=str(cobj.get("message", "") or ""), height=140, disabled=True)

            st.caption(f"Created at: {cobj.get('created_at')} | Updated at: {cobj.get('updated_at')}")

            if st.button("Save Complaint Changes", type="primary", key="btn_save_complaint"):
                ok = update_complaint(selected_cid, {
                    "category": category.strip() if category else "other",
                    "status": status,
                    "assigned_to": assigned_to.strip(),
                    "internal_note": internal_note.strip(),
                })
                if ok:
                    st.success("✅ Complaint updated.")
                    st.rerun()
                else:
                    st.error("❌ Failed to update complaint.")

            # ===== Images section =====
            st.divider()
            st.markdown("#### 🖼️ Attached Images")

            images = cobj.get("images") or []
            if not images:
                st.info("No images attached to this complaint.")
            else:
                for i, img_path in enumerate(images, start=1):
                    p = Path(str(img_path))
                    if not p.exists():
                        st.warning(f"Image not found: {img_path}")
                        continue

                    st.markdown(f"**Image {i}**")
                    try:
                        st.image(str(p), use_container_width=True)
                    except Exception:
                        st.warning(f"Could not display image: {img_path}")

                    # Download button (FIX: pass bytes)
                    try:
                        data = p.read_bytes()
                        st.download_button(
                            label=f"Download Image {i}",
                            data=data,
                            file_name=p.name,
                            mime="image/jpeg" if p.suffix.lower() in [".jpg", ".jpeg"] else "image/png",
                            key=f"dl_{selected_cid}_{i}"
                        )
                    except Exception:
                        pass

# =========================
# TAB 3: Settings
# =========================
with tab3:
    st.info("System settings will be added later.")
