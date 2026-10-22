import base64
import csv
import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from chatbot import FAQChatbot
from llm import GeminiFallback, OUT_OF_TOPIC

# ---------- Settings you can change ----------
BRAND = "Little Aura"
SHOP_URL = ""                  # leave empty until the website exists, then e.g. "https://littleaura.com"
SUPPORT_EMAIL = "support@littleaura.com"
WHATSAPP_NUMBER = ""           # e.g. "8801XXXXXXXXX" (country code, digits only). Empty = use email
TYPING_SECONDS = 0.8
SAVE_HISTORY = False           # True only on your own PC; keep False on the public app
HISTORY_FILE = Path("chats.json")
UNANSWERED_FILE = Path("unanswered.csv")
FEEDBACK_FILE = Path("feedback.csv")
MAX_AI_CALLS = 10              # Gemini calls per visitor session
MAX_QUESTION_CHARS = 300
SUGGEST_MIN = 0.12             # below this, a match is too weak to suggest
GEMINI_MODEL = "gemini-3-flash-preview"

FOOTER_NOTE = f"{BRAND} Assistant is AI and can make mistakes. Please check important information."
WELCOME = (
    f"Hi there! 👋 Welcome to {BRAND}. I'm happy to help. "
    "Ask me about orders, delivery, returns or payments, or pick a topic below."
)
QUICK_REPLIES = [
    "Track my order",
    "Return an item",
    "Payment methods",
    "Contact support",
    "Shipping costs",
    "Discounts and coupons",
]
NO_ANSWER = (
    f"Sorry, I don't have an answer for that right now. "
    f"Please contact {SUPPORT_EMAIL} and we'll help you."
)
OFF_TOPIC = (
    f"Sorry, that's out of topic. I can only help with questions about "
    f"{BRAND}: orders, delivery, payments, returns and our products."
)

st.set_page_config(page_title=f"{BRAND} Assistant", page_icon="🌿")

CSS = """
<style>
.block-container {max-width: 720px; padding-top: 2rem;}
footer {visibility: hidden;}

/* Chat bubbles */
[data-testid="stChatMessage"] {
    border-radius: 18px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.6rem;
    background-color: #E6EEE9;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: #EFE7DA;
}

/* Pill buttons in the main area */
div.stButton > button {
    border-radius: 999px;
    border: 1px solid #5B9A8B;
    background: transparent;
    padding: 0.35rem 1rem;
}
div.stButton > button:hover {
    background-color: #E6EEE9;
    border-color: #5B9A8B;
}

/* Sidebar chat list (flat, left-aligned) */
[data-testid="stSidebar"] div.stButton > button {
    border-radius: 10px;
    border: none;
    justify-content: flex-start;
    text-align: left;
}
[data-testid="stSidebar"] div.stButton > button[kind="primary"],
[data-testid="stSidebar"] div.stButton > button[data-testid="stBaseButton-primary"] {
    background-color: #D3E2DB;
    color: #2F3E46;
}

/* "New chat" button */
.st-key-new_chat button {
    background-color: #5B9A8B;
    color: #14213D;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    padding: 0.6rem 1rem;
    justify-content: center;
    text-align: center;
    box-shadow: 0 2px 6px rgba(91, 154, 139, 0.35);
}
.st-key-new_chat button:hover {
    background-color: #4C8576;
    color: #14213D;
}

[data-testid="stChatInput"] {border-radius: 18px;}

/* Footer note under the message box */
[data-testid="stBottom"]::after {
    content: "__FOOTER__";
    display: block;
    text-align: center;
    font-size: 0.75rem;
    color: #7a8a83;
    padding: 0 0 10px 0;
}
</style>
""".replace("__FOOTER__", FOOTER_NOTE)
st.markdown(CSS, unsafe_allow_html=True)


# ---------- Helpers ----------
def get_secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_row(path, header, row):
    try:
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(header)
            writer.writerow(row)
    except Exception:
        pass  # logging must never break the chat


def log_unanswered(question, source):
    log_row(UNANSWERED_FILE, ["time", "question", "handled_as"], [now(), question, source])


def read_csv(path):
    try:
        return pd.read_csv(path, on_bad_lines="skip")
    except Exception:
        return pd.DataFrame()


def logo_data_uri():
    for name, mime in (("logo.png", "image/png"), ("logo.svg", "image/svg+xml")):
        path = Path("assets") / name
        if path.exists():
            return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
    return None


def brand_html(logo_px=40, title_size="1.7rem"):
    uri = logo_data_uri()
    if uri:
        img = (f'<img src="{uri}" alt="logo" style="height:{logo_px}px;width:{logo_px}px;'
               f'border-radius:50%;object-fit:cover;">')
    else:
        img = f'<span style="font-size:{int(logo_px * 0.8)}px;">🌿</span>'
    inner = (f'<span style="display:inline-flex;align-items:center;gap:10px;color:inherit;">'
             f'{img}<span style="font-size:{title_size};font-weight:700;">{BRAND}</span></span>')
    if SHOP_URL:  # only a link once the website exists
        return (f'<a href="{SHOP_URL}" target="_blank" rel="noopener noreferrer" '
                f'style="text-decoration:none;color:inherit;">{inner}</a>')
    return inner


def human_url():
    if WHATSAPP_NUMBER:
        return f"https://wa.me/{WHATSAPP_NUMBER}?text=Hello%20{BRAND.replace(' ', '%20')}"
    return f"mailto:{SUPPORT_EMAIL}?subject=Help%20with%20my%20order"


# ---------- Admin page (open the app with ?admin=1) ----------
def admin_page():
    st.title("🔒 Admin")
    admin_password = get_secret("ADMIN_PASSWORD")
    if not admin_password:
        st.info("Add ADMIN_PASSWORD to the app's secrets to enable this page.")
        return
    if not st.session_state.get("is_admin"):
        entered = st.text_input("Password", type="password")
        if entered:
            if hmac.compare_digest(entered.encode(), str(admin_password).encode()):
                st.session_state["is_admin"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        return

    st.caption("Logs are stored in files on the server. On free hosting they reset when the app restarts.")
    tab1, tab2 = st.tabs(["Unanswered questions", "Feedback"])
    with tab1:
        df = read_csv(UNANSWERED_FILE)
        if df.empty:
            st.write("Nothing logged yet.")
        else:
            st.metric("Questions with no FAQ match", len(df))
            st.subheader("Most repeated")
            st.dataframe(df["question"].str.lower().str.strip().value_counts().head(10).rename("times asked"))
            st.subheader("All (newest first)")
            st.dataframe(df.iloc[::-1])
            st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                               "unanswered.csv", "text/csv")
    with tab2:
        fb = read_csv(FEEDBACK_FILE)
        if fb.empty:
            st.write("No feedback yet.")
        else:
            c1, c2 = st.columns(2)
            c1.metric("👍 helpful", int((fb["rating"] == 1).sum()))
            c2.metric("👎 not helpful", int((fb["rating"] == 0).sum()))
            st.subheader("Answers marked 👎 (newest first)")
            st.dataframe(fb[fb["rating"] == 0].iloc[::-1])
            st.download_button("Download CSV", fb.to_csv(index=False).encode("utf-8"),
                               "feedback.csv", "text/csv")


if st.query_params.get("admin") == "1":
    admin_page()
    st.stop()


# ---------- Bot, AI fallback, state ----------
@st.cache_resource
def load_bot():
    return FAQChatbot()


bot = load_bot()


@st.cache_resource
def load_ai():
    key = get_secret("GEMINI_API_KEY")
    if not key:
        return None
    return GeminiFallback(key, bot.faqs, model=get_secret("GEMINI_MODEL", GEMINI_MODEL))


ai = load_ai()
st.session_state.setdefault("ai_calls", 0)
st.session_state.setdefault("pending", None)


def make_reply(answer, score, matched, source, suggestions=None, related=None):
    return {"answer": answer, "score": score, "matched": matched, "source": source,
            "suggestions": suggestions or [], "related": related or []}


def get_reply(prompt):
    if not re.search(r"[A-Za-z0-9]", prompt):
        return make_reply("Please type a question.", 0.0, None, "empty")

    # A suggestion or topic button was clicked: the text is an exact FAQ question
    if prompt in bot.answer_of:
        return make_reply(bot.answer_of[prompt], 1.0, prompt, "faq", related=bot.related(prompt))

    answer, score, matched = bot.get_answer(prompt)
    if matched:
        return make_reply(answer, score, matched, "faq", related=bot.related(matched))

    close = bot.suggest(prompt, 3)
    # Weak but close: offer choices instead of guessing (no API call needed)
    if close and close[0][1] >= SUGGEST_MIN:
        return make_reply("I'm not sure I understood. Did you mean one of these?",
                          score, None, "suggest", suggestions=[q for q, _ in close])

    # Nothing close: ask Gemini, if available and within this visitor's limit
    fallback = make_reply(NO_ANSWER, score, None, "none", suggestions=[q for q, _ in close])
    if ai is None or st.session_state.ai_calls >= MAX_AI_CALLS:
        return fallback
    try:
        st.session_state.ai_calls += 1
        reply = ai.ask(prompt[:MAX_QUESTION_CHARS])
    except Exception:
        return fallback
    if not reply:
        return fallback
    if reply.upper().startswith(OUT_OF_TOPIC):
        return make_reply(OFF_TOPIC, score, None, "off")
    return make_reply(reply, score, None, "ai")


# ---------- Saving and loading chat history ----------
def load_chats():
    if not SAVE_HISTORY:
        return {}
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_chats():
    if not SAVE_HISTORY:
        return
    to_save = {cid: c for cid, c in st.session_state.chats.items() if len(c["messages"]) > 1}
    HISTORY_FILE.write_text(json.dumps(to_save, ensure_ascii=False, indent=2), encoding="utf-8")


def new_chat():
    cid = uuid.uuid4().hex[:8]
    st.session_state.chats[cid] = {
        "title": "New chat",
        "messages": [{"role": "assistant", "content": WELCOME}],
    }
    st.session_state.current = cid


def save_feedback(msg):
    value = st.session_state.get(f"fb_{msg['id']}")
    if value is None:
        return
    msg["rating"] = int(value)  # 1 = thumbs up, 0 = thumbs down
    log_row(FEEDBACK_FILE,
            ["time", "rating", "question", "answer", "handled_as", "matched_faq"],
            [now(), msg["rating"], msg.get("question", ""), msg["content"],
             msg.get("source", ""), msg.get("matched") or ""])
    save_chats()


if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
    new_chat()  # every visit starts on a fresh chat

chat = st.session_state.chats[st.session_state.current]
messages = chat["messages"]

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(brand_html(32, "1.3rem"), unsafe_allow_html=True)
    st.write("")
    if st.button("＋  New chat", key="new_chat", use_container_width=True):
        if len(messages) > 1:
            new_chat()
        st.rerun()

    query = st.text_input("Search chats", placeholder="🔍 Search chats",
                          label_visibility="collapsed", key="chat_search").strip().lower()

    def chat_matches(c):
        if not query:
            return True
        return query in c["title"].lower() or any(query in m["content"].lower() for m in c["messages"])

    st.caption("Recent chats")
    saved = [(cid, c) for cid, c in reversed(list(st.session_state.chats.items()))
             if len(c["messages"]) > 1 and chat_matches(c)]
    if not saved:
        st.caption("No chats found." if query else "No conversations yet.")
    for cid, c in saved:
        col_open, col_del = st.columns([5, 1], vertical_alignment="center")
        is_active = cid == st.session_state.current
        if col_open.button(c["title"], key=f"open_{cid}", use_container_width=True,
                           type="primary" if is_active else "secondary"):
            st.session_state.current = cid
            st.rerun()
        if col_del.button("🗑", key=f"del_{cid}", help="Delete this chat"):
            del st.session_state.chats[cid]
            if is_active:
                new_chat()
            save_chats()
            st.rerun()

    st.divider()
    st.link_button("💬 Talk to a human", human_url(), use_container_width=True)
    st.caption("Please don't share personal details such as card numbers in this chat.")
    st.checkbox("Show matched question and score", key="show_debug")

# ---------- Header ----------
st.markdown(brand_html(46, "2rem"), unsafe_allow_html=True)
st.subheader("How can we help?")
st.caption(f"The {BRAND} assistant answers common questions instantly.")

# ---------- Conversation ----------
def render_feedback(msg):
    if msg.get("rating") is not None:
        st.caption("👍 Thanks for the feedback!" if msg["rating"] == 1
                   else "👎 Thanks, we'll use this to improve.")
        return
    st.feedback("thumbs", key=f"fb_{msg['id']}", on_change=save_feedback, args=(msg,))


for msg in messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("source") == "ai":
            st.caption("✨ AI-generated answer. Please confirm anything important with support.")
        if msg.get("matched") and st.session_state.get("show_debug"):
            st.caption(f"Matched: {msg['matched']} (similarity {msg['score']:.2f})")
        if msg["role"] == "assistant" and msg.get("id") and msg.get("source") != "empty":
            render_feedback(msg)

# ---------- Buttons under the latest answer ----------
last = messages[-1]
if last["role"] == "assistant" and last.get("id"):
    source = last.get("source")
    options, label = [], ""
    if source == "suggest":
        options, label = last.get("suggestions", []), "Did you mean:"
    elif source == "faq":
        options, label = last.get("related", []), "You may also ask:"
    elif source == "none":
        options, label = last.get("suggestions", []), "Maybe one of these helps:"
    if options:
        st.caption(label)
        for j, q in enumerate(options):
            if st.button(q, key=f"opt_{last['id']}_{j}", use_container_width=True):
                st.session_state.pending = q
                st.rerun()
    if source in ("none", "ai"):
        st.link_button("💬 Talk to a human", human_url())

# ---------- Quick replies and topic browser ----------
if len(messages) == 1 and not st.session_state.pending:
    cols = st.columns(2)
    for i, text in enumerate(QUICK_REPLIES):
        if cols[i % 2].button(text, key=f"quick_{i}", use_container_width=True):
            st.session_state.pending = text
            st.rerun()

topics = bot.topics()
with st.expander("📚 Browse topics", expanded=(len(messages) == 1)):
    tabs = st.tabs(list(topics.keys()))
    for tab, (category, questions) in zip(tabs, topics.items()):
        with tab:
            for j, q in enumerate(questions):
                if st.button(q, key=f"topic_{category}_{j}", use_container_width=True):
                    st.session_state.pending = q
                    st.rerun()

# ---------- Input ----------
prompt = st.chat_input("Type your question here...")
if st.session_state.pending:
    prompt = st.session_state.pending
    st.session_state.pending = None

if prompt:
    messages.append({"role": "user", "content": prompt})
    if chat["title"] == "New chat":
        chat["title"] = prompt[:28] + ("…" if len(prompt) > 28 else "")

    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Typing..."):
            time.sleep(TYPING_SECONDS)
            reply = get_reply(prompt)

    if reply["source"] in ("suggest", "ai", "off", "none"):
        log_unanswered(prompt, reply["source"])

    messages.append({
        "role": "assistant",
        "content": reply["answer"],
        "matched": reply["matched"],
        "score": reply["score"],
        "source": reply["source"],
        "suggestions": reply["suggestions"],
        "related": reply["related"],
        "id": uuid.uuid4().hex[:8],
        "question": prompt,
    })
    save_chats()
    st.rerun()