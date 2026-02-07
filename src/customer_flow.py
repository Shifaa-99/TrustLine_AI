import json
import re
from enum import Enum
from typing import Optional, Dict, List, Any

from complaint_manager import create_complaint_record
from order_manager import _load_orders, find_orders_by_phone, normalize_phone


# ============================================================
# Conversation States (FSM)
# ============================================================

class State(str, Enum):
    IDLE = "idle"
    AWAITING_ORDER_ID = "awaiting_order_id"
    AWAITING_PHONE = "awaiting_phone"
    VERIFIED = "verified"


# ============================================================
# Session Object
# ============================================================

class CustomerSession:
    def __init__(self):
        self.state: State = State.IDLE
        self.order_id: Optional[str] = None
        self.order_data: Optional[Dict[str, Any]] = None
        self.rag = None
        self.matched_orders: List[str] = []
        self.language: Optional[str] = None  # "ar" or "en"
        self.chat_history: List[Dict[str, str]] = []
        self.awaiting_images: bool = False


        # Keep last described issue + pending images (from UI)
        self.last_issue_text: Optional[str] = None
        self.pending_image_paths: List[str] = []

    def add_turn(self, role: str, content: str):
        if not content:
            return
        self.chat_history.append({"role": role, "content": content})

    def recent_history(self, max_turns: int = 10) -> List[Dict[str, str]]:
        if max_turns <= 0:
            return []
        return self.chat_history[-max_turns:]


# ============================================================
# Helpers
# ============================================================

def extract_digits(text: str) -> str:
    return re.sub(r"\D", "", (text or ""))

def looks_like_phone(text: str) -> bool:
    d = extract_digits(text)
    # مناسب للأردن والخليج عادة، عدّل لو بدك
    return 9 <= len(d) <= 15

def looks_like_order_id(text: str) -> bool:
    t = (text or "").strip().upper()
    return t.startswith("ORD-") and len(t) >= 6

def detect_language(text: str) -> Optional[str]:
    t = (text or "").strip()
    if not t:
        return None

    # Neutral inputs (do NOT lock language)
    if looks_like_order_id(t) or looks_like_phone(t):
        return None

    # Arabic?
    if re.search(r"[\u0600-\u06FF]", t):
        return "ar"

    # English letters?
    if re.search(r"[A-Za-z]", t):
        return "en"

    return None

def user_says_dont_know_order(text: str) -> bool:
    t = (text or "").strip().lower()
    arabic = ["ما بعرف", "مش عارف", "ما عندي رقم", "نسيت رقم", "مش متذكر", "ما بتذكر", "ما معي رقم"]
    english = ["don't know", "do not know", "no order id", "forgot", "i don't remember"]
    return any(p in t for p in arabic + english)

def retrieve_knowledge(query: str, rag_store) -> str:
    if not rag_store:
        return ""
    docs = rag_store.similarity_search(query, k=3)
    return "\n".join(d.page_content for d in docs)

def is_policy_intent(text: str) -> bool:
    t = (text or "").strip().lower()
    keywords_ar = ["سياسة", "سياسات", "استرجاع", "ارجاع", "إرجاع", "استبدال", "ضمان", "خصوصية", "شروط", "توصيل", "استرداد"]
    keywords_en = ["policy", "refund", "return", "exchange", "warranty", "privacy", "terms", "delivery"]
    return any(k in t for k in keywords_ar + keywords_en)

def is_order_intent(text: str) -> bool:
    t = (text or "").strip().lower()
    keywords_ar = ["طلبي", "طلبيتي", "طلب", "رقم الطلب", "تتبع", "وين طلبي", "تاخر", "تأخر", "توصيل", "شحنة", "مندوب", "سائق"]
    keywords_en = ["order", "track", "tracking", "delivery", "delayed", "shipment", "courier", "driver"]
    return (
        any(k in t for k in keywords_ar + keywords_en)
        or looks_like_order_id(text)
        or looks_like_phone(text)
    )

def is_escalation_request(text: str) -> bool:
    t = (text or "").strip().lower()
    ar = ["مدير", "مسؤول", "الإدارة", "تصعيد", "اشكي", "شكوى", "ارفع شكوى", "ارفعها", "شكيت", "بدي حد مسؤول"]
    en = ["manager", "supervisor", "escalate", "complaint", "raise a complaint"]
    return any(k in t for k in ar + en)

def is_yes(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in ["نعم", "اه", "آه", "ايوه", "اي", "yes", "yep", "yeah", "ok", "تمام", "تم", "تأكيد", "أكد", "confirm"]

def last_assistant_asked_escalation(session: CustomerSession) -> bool:
    for m in reversed(session.chat_history):
        if m.get("role") == "assistant":
            a = (m.get("content") or "").lower()
            return ("تصعيد" in a) or ("مسؤول" in a) or ("الإدارة" in a) or ("manager" in a) or ("escalat" in a)
    return False


# ============================================================
# Complaint classifiers (verified stage)
# ============================================================

def is_post_delivery_complaint(text: str) -> bool:
    t = (text or "").lower()
    ar = ["تلف", "مكسور", "خربان", "ناقص", "تالف", "فتح", "مفتوح", "وصلني غلط", "منتج غلط", "غلط بالطلب", "مشكلة بالمنتج"]
    en = ["damage", "damaged", "broken", "missing", "defect", "opened", "wrong item", "wrong product"]
    return any(k in t for k in ar + en)

def is_general_complaint(text: str) -> bool:
    t = (text or "").lower()
    ar = [
        "تأخير", "تاخير", "تاخر", "تأخر", "متأخر",
        "سوء", "تعامل", "مندوب", "سائق", "درايفر",
        "مش محترم", "وقح", "اسلوب", "خدمة سيئة", "توصيل سيء"
    ]
    en = ["delay", "late", "bad service", "rude", "courier", "driver", "behavior", "attitude"]
    return any(k in t for k in ar + en)


# ============================================================
# Core Entry Point
# ============================================================

def handle_customer_message(user_text: str, session: CustomerSession, llm) -> str:
    user_text = (user_text or "").strip()
    if not user_text:
        return ""

    # Normalize order id input (case-insensitive)
    if looks_like_order_id(user_text):
        user_text = user_text.strip().upper()

    # Lock language from first meaningful message
    if session.language is None:
        lang = detect_language(user_text)
        if lang:
            session.language = lang

    orders = _load_orders()
    rag_context = retrieve_knowledge(user_text, session.rag)

    # Always store user message in memory
    session.add_turn("user", user_text)

    # ========================================================
    # GLOBAL: Escalation request BEFORE verification
    # Prevent LLM from claiming "recorded" while not saved
    # ========================================================
    if session.state != State.VERIFIED and is_escalation_request(user_text):
        session.last_issue_text = user_text
        session.state = State.AWAITING_ORDER_ID

        reply_ar = "أكيد. عشان أسجل الشكوى بشكل صحيح، اكتب رقم الطلب (مثال: ORD-001) أو إذا ما بتعرفه اكتب رقم هاتفك."
        reply_en = "Sure. To file your request properly, type your Order ID (e.g., ORD-001). If you don’t know it, type your phone number."
        reply = reply_ar if session.language != "en" else reply_en

        session.add_turn("assistant", reply)
        return reply

    # ========================================================
    # STATE: IDLE
    # ========================================================
    if session.state == State.IDLE:
        if is_policy_intent(user_text) and not is_order_intent(user_text):
            reply = generate_llm_reply(
                llm,
                State.IDLE,
                {"verified": False, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        if is_order_intent(user_text):
            session.state = State.AWAITING_ORDER_ID
            reply = generate_llm_reply(
                llm,
                State.AWAITING_ORDER_ID,
                {"verified": False, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        reply = generate_llm_reply(
            llm,
            State.IDLE,
            {"verified": False, "knowledge": rag_context, "language": session.language},
            user_text,
            session.recent_history(10),
        )
        session.add_turn("assistant", reply)
        return reply

    # ========================================================
    # STATE: AWAITING ORDER ID
    # ========================================================
    if session.state == State.AWAITING_ORDER_ID:

        # If user selects matched order
        if session.matched_orders and user_text in session.matched_orders:
            session.order_id = user_text
            order = orders.get(session.order_id)
            if not order:
                session.state = State.IDLE
                session.order_id = None
                session.matched_orders = []
                
                reply = "تمام. للتأكد من الأمان، اكتب رقم هاتفك المرتبط بالطلب."
                if session.language == "en":
                    reply = "Great. For security, please type the phone number linked to this order."
                session.add_turn("assistant", reply)
                return reply


            # ✅ Require phone after selecting order
            session.state = State.AWAITING_PHONE
            session.matched_orders = []
            session.order_data = {
                "order_id": session.order_id,
                "customer_name": order.get("customer_name", ""),
                "status": order.get("status", ""),
                "last_updated": order.get("last_updated", ""),
                "phone": order.get("phone", ""),
            }

            reply = generate_llm_reply(
                llm, State.AWAITING_PHONE,
                {"verified": False, "order_exists": True, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        # Order id format but not found
        if looks_like_order_id(user_text) and user_text not in orders:
            session.state = State.IDLE
            session.order_id = None
            session.matched_orders = []
            reply = generate_llm_reply(
                llm, State.IDLE,
                {"verified": False, "order_exists": False, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        # user doesn't know order id
        if user_says_dont_know_order(user_text):
            session.order_id = None
            session.matched_orders = []
            session.state = State.AWAITING_PHONE
            reply = generate_llm_reply(
                llm, State.AWAITING_PHONE,
                {"verified": False, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        # phone provided
        if looks_like_phone(user_text):
            phone = normalize_phone(extract_digits(user_text))
            matches = find_orders_by_phone(phone)

            if not matches:
                session.matched_orders = []
                reply = generate_llm_reply(
                    llm, session.state,
                    {"verified": False, "reason": "no_order_for_phone", "knowledge": rag_context, "language": session.language},
                    user_text,
                    session.recent_history(10),
                )
                session.add_turn("assistant", reply)
                return reply

            session.matched_orders = matches

            if len(matches) > 1:
                lines = []
                for oid in matches:
                    o = orders.get(oid, {})
                    lines.append(
                        f"- {oid} | الحالة: {o.get('status', '-')}"
                        if (session.language == "ar") else
                        f"- {oid} | status: {o.get('status','-')}"
                    )
                msg_ar = "تم العثور على أكثر من طلب مرتبط برقم هاتفك:\n" + "\n".join(lines) + "\n\nمن فضلك اكتب رقم الطلب حتى أكمل مساعدتك."
                msg_en = "We found multiple orders linked to your phone:\n" + "\n".join(lines) + "\n\nPlease type the Order ID to continue."
                reply = msg_ar if session.language == "ar" else msg_en
                session.add_turn("assistant", reply)
                return reply

            # single match -> verify
            session.order_id = matches[0]
            order = orders.get(session.order_id, {})
            session.state = State.VERIFIED
            session.matched_orders = []
            session.order_data = {
                "order_id": session.order_id,
                "customer_name": order.get("customer_name", ""),
                "status": order.get("status", ""),
                "last_updated": order.get("last_updated", ""),
                "phone": order.get("phone", ""),
            }
            
  
            reply = generate_llm_reply(
                llm, State.VERIFIED,
                {"verified": True, "order": session.order_data, "reveal_order_id": True, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        # valid existing order id -> ask phone
        if user_text in orders:
            session.order_id = user_text
            session.matched_orders = []
            session.state = State.AWAITING_PHONE

            reply_ar = "تمام ✅ للتأكد من الأمان، اكتب رقم هاتفك المرتبط بالطلب."
            reply_en = "Great ✅ For security, please type the phone number linked to the order."
            reply = reply_en if session.language == "en" else reply_ar

            session.add_turn("assistant", reply)
            return reply


        # fallback
        reply = generate_llm_reply(
            llm, session.state,
            {"verified": False, "knowledge": rag_context, "language": session.language},
            user_text,
            session.recent_history(10),
        )
        session.add_turn("assistant", reply)
        return reply

    # ========================================================
    # STATE: AWAITING PHONE
    # ========================================================
    if session.state == State.AWAITING_PHONE:
        if not looks_like_phone(user_text):
            reply = generate_llm_reply(
                llm, session.state,
                {"verified": False, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        phone = normalize_phone(extract_digits(user_text))
        matches = find_orders_by_phone(phone)

        if not matches:
            reply = generate_llm_reply(
                llm, session.state,
                {"verified": False, "phone_match": False, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        if session.order_id and session.order_id not in matches:
            reply = generate_llm_reply(
                llm, session.state,
                {"verified": False, "phone_match": False, "knowledge": rag_context, "language": session.language},
                user_text,
                session.recent_history(10),
            )
            session.add_turn("assistant", reply)
            return reply

        if not session.order_id:
            if len(matches) > 1:
                session.matched_orders = matches
                session.state = State.AWAITING_ORDER_ID

                lines = []
                for oid in matches:
                    o = orders.get(oid, {})
                    lines.append(
                        f"- {oid} | الحالة: {o.get('status', '-')}"
                        if (session.language == "ar") else
                        f"- {oid} | status: {o.get('status','-')}"
                    )

                msg_ar = "وجدنا أكثر من طلب مرتبط برقم هاتفك:\n" + "\n".join(lines) + "\n\nمن فضلك اكتب رقم الطلب المقصود."
                msg_en = "We found multiple orders linked to your phone:\n" + "\n".join(lines) + "\n\nPlease type the intended Order ID."
                reply = msg_ar if session.language == "ar" else msg_en
                session.add_turn("assistant", reply)
                return reply

            session.order_id = matches[0]

        order = orders.get(session.order_id, {})
        session.state = State.VERIFIED
        session.matched_orders = []
        session.order_data = {
            "order_id": session.order_id,
            "customer_name": order.get("customer_name", ""),
            "status": order.get("status", ""),
            "last_updated": order.get("last_updated", ""),
            "phone": order.get("phone", ""),
        }

        reply = generate_llm_reply(
            llm, State.VERIFIED,
            {"verified": True, "order": session.order_data, "reveal_order_id": True, "knowledge": rag_context, "language": session.language},
            user_text,
            session.recent_history(10),
        )
        session.add_turn("assistant", reply)
        return reply

    # ========================================================
    # STATE: VERIFIED
    # ========================================================
    if session.state == State.VERIFIED:

        # لو المستخدم كتب تأكيد بدون وجود صور/شكوى معلقة
        if is_yes(user_text) and not (session.pending_image_paths or []) and not (session.last_issue_text or ""):
            reply_ar = "تمام ✅ إذا بدك تسجل شكوى، اكتب وصف المشكلة التي واجهتك و مستاء بسببهاأولاً."
            reply_en = "Okay ✅ If you want to file a complaint, please describe the issue you faced and what upset you about it first."
            reply = reply_en if session.language == "en" else reply_ar
            session.add_turn("assistant", reply)
            return reply
        
        # لو النظام منتظر صور والمستخدم كتب تأكيد بدون صور
        if session.awaiting_images and is_yes(user_text) and not (session.pending_image_paths or []):
            reply_ar = "تمام ✅ بس لسه ما وصلني صور. ارفق الصور من (Attach Images) وبعدها اكتب (تم/تأكيد)."
            reply_en = "Okay ✅ but I still didn't receive any images. Attach them using (Attach Images), then type (confirm/yes)."
            reply = reply_en if session.language == "en" else reply_ar
            session.add_turn("assistant", reply)
            return reply


        # Store last issue text (don't overwrite with yes/confirm)
        if not is_yes(user_text):
            session.last_issue_text = user_text

        order_status = (session.order_data or {}).get("status", "")

        # 0) General complaints (delay/service/driver) -> NO delivery / NO images
        if is_general_complaint(user_text):
            rec = create_complaint_record(
                order_id=session.order_data.get("order_id", "") if session.order_data else (session.order_id or ""),
                customer_name=session.order_data.get("customer_name", "") if session.order_data else "",
                phone=session.order_data.get("phone", "") if session.order_data else "",
                message=session.last_issue_text or user_text,
                image_paths=[],
                category="service",
            )
            session.pending_image_paths = []
            session.last_issue_text = None

            reply = f"✅ تم تسجيل شكواك بنجاح.\nرقم الشكوى: {rec['complaint_id']}"
            if session.language == "en":
                reply = f"✅ Your complaint has been recorded.\nComplaint ID: {rec['complaint_id']}"
            session.add_turn("assistant", reply)
            return reply

        # 1) Post-delivery complaints -> delivered + images
        if is_post_delivery_complaint(user_text):
            if order_status != "delivered":
                reply = "يمكن تسجيل شكاوى التلف/النقص فقط بعد تسليم الطلب."
                if session.language == "en":
                    reply = "Damage/missing complaints can only be submitted after delivery."
                session.add_turn("assistant", reply)
                return reply

            if not (session.pending_image_paths or []):
                session.awaiting_images = True
                reply = "تمام. أرفق صور المشكلة من خيار (Attach Images) ثم اكتب (تم/تأكيد) لإرسال الشكوى."
                if session.language == "en":
                    reply = "Okay. Attach images using (Attach Images), then type (confirm/yes) to submit."
                session.add_turn("assistant", reply)
                return reply

            # If delivered + images already attached -> submit immediately
            rec = create_complaint_record(
                order_id=session.order_data.get("order_id", "") if session.order_data else (session.order_id or ""),
                customer_name=session.order_data.get("customer_name", "") if session.order_data else "",
                phone=session.order_data.get("phone", "") if session.order_data else "",
                message=session.last_issue_text or user_text,
                image_paths=session.pending_image_paths,
                category="damage",
            )
            session.pending_image_paths = []
            session.last_issue_text = None
            if session.language == "ar":
                reply = (
                    "نعتذر عن الإزعاج اللي واجهته 🙏\n"
                    "✅ تم تسجيل شكواك بنجاح، وسيتم متابعتها من قبل فريق الدعم.\n\n"
                    f"رقم الشكوى:\n{rec['complaint_id']}\n\n"
                    "هل في شيء ثاني أقدر أساعدك فيه؟"
                )
            else:        
                reply = (
                    "We’re sorry for the inconvenience you experienced 🙏\n"
                    "Your complaint has been successfully recorded and will be reviewed by our support team.✅\n\n"
                    f"Complaint ID:\n{rec['complaint_id']}"
                    )

            session.add_turn("assistant", reply)
            return reply

        # ✅ If images are attached and user confirms -> submit last issue (for damage case)
        if (session.pending_image_paths or []) and session.last_issue_text and is_yes(user_text):
            rec = create_complaint_record(
                order_id=session.order_data.get("order_id", "") if session.order_data else (session.order_id or ""),
                customer_name=session.order_data.get("customer_name", "") if session.order_data else "",
                phone=session.order_data.get("phone", "") if session.order_data else "",
                message=session.last_issue_text,
                image_paths=session.pending_image_paths,
                category="damage",
            )
            session.pending_image_paths = []
            session.last_issue_text = None
            session.awaiting_images = False

            if session.language == "ar":
                reply = (
                    "نعتذر عن الإزعاج اللي واجهته 🙏\n"
                    "✅ تم تسجيل شكواك بنجاح، وسيتم متابعتها من قبل فريق الدعم.\n\n"
                    f"رقم الشكوى:\n{rec['complaint_id']}\n\n"
                    "هل في شيء ثاني أقدر أساعدك فيه؟"
                )
            else:        
                reply = (
                    "We’re sorry for the inconvenience you experienced 🙏\n"
                    "Your complaint has been successfully recorded and will be reviewed by our support team.✅\n\n"
                    f"Complaint ID:\n{rec['complaint_id']}"
                    )

            session.add_turn("assistant", reply)
            return reply

        # 2) Escalation/Manager -> record without images (verified only)
        if is_escalation_request(user_text) or (is_yes(user_text) and last_assistant_asked_escalation(session)):
            rec = create_complaint_record(
                order_id=session.order_data.get("order_id", "") if session.order_data else (session.order_id or ""),
                customer_name=session.order_data.get("customer_name", "") if session.order_data else "",
                phone=session.order_data.get("phone", "") if session.order_data else "",
                message=session.last_issue_text or user_text,
                image_paths=[],
                category="escalation",
            )
            session.pending_image_paths = []
            session.last_issue_text = None

            reply = f"✅ تم تسجيل طلبك.\nرقم الشكوى: {rec['complaint_id']}"
            if session.language == "en":
                reply = f"✅ Your request has been recorded.\nComplaint ID: {rec['complaint_id']}"
            session.add_turn("assistant", reply)
            return reply

        # 3) Otherwise -> normal LLM
        reply = generate_llm_reply(
            llm, State.VERIFIED,
            {"verified": True, "order": session.order_data, "knowledge": rag_context, "language": session.language},
            user_text,
            session.recent_history(10),
        )
        session.add_turn("assistant", reply)
        return reply


# ============================================================
# Prompt Delegation
# ============================================================

def generate_llm_reply(llm, system_state: State, context: Dict, user_text: str, history: List[Dict[str, str]]) -> str:
    knowledge = context.get("knowledge", "") or ""
    context_no_knowledge = dict(context)
    context_no_knowledge.pop("knowledge", None)

    system_prompt = f"""
=====================
KNOWLEDGE (Policies / FAQs)
=====================
{knowledge}

You are an AI Customer Support Assistant for an e-commerce platform.

=====================
CRITICAL RULES
=====================


LANGUAGE POLICY (LOCKED):
- You are ONLY allowed to respond in Arabic or English.
- You are STRICTLY FORBIDDEN from responding in any other language (French, Spanish, etc.).
- The conversation language is LOCKED from the customer's FIRST message.
- You MUST always respond in this locked language, even if the customer later mixes languages.
- Locked language is provided in CONTEXT as "language": "ar" or "en".
- If the user writes mixed language, keep the locked language and answer normally.
- If CONTEXT language == "ar": respond ONLY in Arabic.
- If CONTEXT language == "en": respond ONLY in English.
- If CONTEXT language is empty: respond in the same language as the most recent user message.
- Never claim the user selected a language unless explicitly stated.

DATA & PRIVACY:
- You must NOT invent any order, phone number, customer, or policy information.
- You must rely ONLY on the CONTEXT provided by the system.
- You must NOT reveal any order information unless verification is complete.

RAG ENFORCEMENT:
- If the requested information is NOT explicitly present in the KNOWLEDGE section:
  - You MUST clearly state that this information is not available.
  - You MUST NOT answer based on general knowledge, assumptions, or common practices.
  - You MUST NOT guess, approximate, or fabricate policies.

RAG INTERPRETATION RULE:
- If the KNOWLEDGE section contains information that semantically answers the user's question
  (even if wording or language differs),
  you SHOULD use it to answer accurately.   

ALLOWED USER DATA:
- Order ID
- Phone number
You must NEVER ask for:
- Email
- Address
- Any personal data not listed above

=====================
CONVERSATION RULES
=====================

SYSTEM STATE AWARENESS:
- Always respect the CURRENT SYSTEM STATE.
- If verification is incomplete, ask ONLY for the missing required information.
- Ask for ONE piece of information at a time.

ORDER VERIFICATION FLOW:
- If the user does NOT know the order ID:
  - Ask for the phone number instead.
  - If the phone number matches an existing order:
    - Politely provide the order ID.
    - Then continue the conversation normally.

PHONE VERIFICATION:
- If the provided phone number does not match the order:
  - Politely refuse to share any order details.
  - Do NOT ask additional questions.

ORDER NOT FOUND:
- If the order does not exist:
  - Apologize briefly.
  - Clearly state that no order was found.
  - Do NOT guess or speculate.

DELIVERY STATE RULES:
- You MUST check the order status before responding to any complaint.
- If the order status is NOT "delivered":
  - You MUST NOT accept complaints about damage, defects, or missing items.
  - You MUST politely inform the customer that the order has not been delivered yet.
  - You MUST explain that complaints can only be submitted after delivery.
- ONLY if order status is "delivered":
  - You may proceed with damage or defect complaints.

ESCALATION / MANAGER REQUEST:

- If the user asks to speak with a manager or a responsible person:

  • If order verification IS complete:
    - Do NOT ask for more information.
    - Do NOT make promises.
    - Respond with a confirmation that the request was recorded
      and that support will contact the customer.

  • If order verification is NOT complete:
    - Do NOT claim that the request or complaint was recorded.
    - Ask politely for the missing required information
      (Order ID OR phone number, one at a time)
      in order to proceed with filing the request.

EMOTIONAL HANDLING (DE-ESCALATION):
- If the user is angry, frustrated, or uses harsh language:
  - Start with a short empathetic sentence in the locked language.
  - Keep the tone calm, respectful, and solution-focused.
  - Do NOT mirror the user's anger.
  - Do NOT escalate the tone.
  - Stay professional at all times.
  - Offer the next clear step (one question at a time) without being defensive.

STRICT RESPONSE RULE:
- You MUST NOT describe internal actions such as:
  "checking", "looking up", "verifying", "one moment"
- You MUST respond ONLY with the final result.  

RAG USAGE:
- You may use KNOWLEDGE only for general policies and FAQs.
- You must NOT use knowledge for order verification or identity checks.

IMPORTANT:
- If verification has JUST been completed:
  - You MUST acknowledge successful verification.
  - You MUST ask the customer how you can help next.
  - You MUST NOT claim that any complaint or request was recorded unless explicitly stated in CONTEXT.

=====================
CURRENT SYSTEM STATE:
{system_state}

CONTEXT:
{json.dumps(context_no_knowledge, ensure_ascii=False)}
""".strip()

    messages = [{"role": "system", "content": system_prompt}]

    for m in (history or []):
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    if not messages or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": user_text})

    return llm.invoke(messages).content.strip()
