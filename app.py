import json
import time
import uuid
from pathlib import Path

import streamlit as st
from chatbot import FAQChatbot

import os
import re
from llm import GeminiFallback, OUT_OF_TOPIC

# ---------- Settings you can change ----------
MAX_AI_CALLS = 10      # Gemini calls allowed per visitor session (protects your quota)
MAX_QUESTION_CHARS = 300
GEMINI_MODEL = "gemini-3-flash-preview"
NO_ANSWER = (
    "Sorry, I don't have an answer for that right now. "
    "Please contact support@littleaura.com and we'll help you."
)
OFF_TOPIC = (
    "Sorry, that's out of topic. I can only help with questions about "
    "Little Aura: orders, delivery, payments, returns and our products."
)

BRAND = "Little Aura"                 # your store / company name
TYPING_SECONDS = 0.8           # pause before the bot answers
HISTORY_FILE = Path("chats.json")
SAVE_HISTORY = False   # keep False when the app is public; True only on your own PC
WELCOME = (
    "Hi there! 👋 Welcome to Little Aura. I'm happy to help. "
    "Ask me about orders, delivery, returns or payments, or pick a topic below."
)
SUGGESTIONS = [
    "Track my order",
    "Return an item",
    "Payment methods",
    "Contact support",
    "Shipping costs",
    "Discounts and coupons",
]

st.set_page_config(page_title=f"{BRAND} Help", page_icon="💬")

st.markdown(
    """
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

    /* Quick-reply buttons (pill shape) */
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

    [data-testid="stChatInput"] {border-radius: 18px;}

        /* "New chat" button: filled, rounded, stands out from the chat list */
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

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Saving and loading chat history ----------
def load_chats():
    if not SAVE_HISTORY:
        return {}
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    # try:
    #     return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    # except Exception:
    #     return {}


def save_chats():
    if not SAVE_HISTORY:
        return
    # Only save chats that contain at least one customer message
    to_save = {
        cid: chat
        for cid, chat in st.session_state.chats.items()
        if len(chat["messages"]) > 1
    }
    HISTORY_FILE.write_text(
        json.dumps(to_save, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def new_chat():
    cid = uuid.uuid4().hex[:8]
    st.session_state.chats[cid] = {
        "title": "New chat",
        "messages": [{"role": "assistant", "content": WELCOME}],
    }
    st.session_state.current = cid


@st.cache_resource
def load_bot():
    return FAQChatbot()


bot = load_bot()

def get_secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


@st.cache_resource
def load_ai():
    key = get_secret("GEMINI_API_KEY")
    if not key:
        return None
    return GeminiFallback(key, bot.faqs, model=get_secret("GEMINI_MODEL", GEMINI_MODEL))


ai = load_ai()
st.session_state.setdefault("ai_calls", 0)


def get_reply(prompt):
    """Returns (answer, score, matched_faq, source)."""
    if not re.search(r"[A-Za-z0-9]", prompt):
        return "Please type a question.", 0.0, None, "none"

    answer, score, matched = bot.get_answer(prompt)
    if matched:
        return answer, score, matched, "faq"

    # No FAQ matched: ask Gemini (if available and within this visitor's limit)
    if ai is None or st.session_state.ai_calls >= MAX_AI_CALLS:
        return NO_ANSWER, score, None, "none"
    try:
        st.session_state.ai_calls += 1
        reply = ai.ask(prompt[:MAX_QUESTION_CHARS])
    except Exception:
        return NO_ANSWER, score, None, "none"

    if not reply:
        return NO_ANSWER, score, None, "none"
    if reply.upper().startswith(OUT_OF_TOPIC):
        return OFF_TOPIC, score, None, "off"
    return reply, score, None, "ai"

if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
    st.session_state.pending = None
    new_chat()  # every visit starts on a fresh chat

chat = st.session_state.chats[st.session_state.current]
messages = chat["messages"]

# ---------- Sidebar ----------
with st.sidebar:
    st.header(f"💬 {BRAND}")
    if st.button("＋  New chat", key="new_chat", use_container_width=True):
        if len(messages) > 1:  # don't pile up empty chats
            new_chat()
        st.rerun()

    st.caption("Recent chats")
    saved = [
        (cid, c)
        for cid, c in reversed(list(st.session_state.chats.items()))
        if len(c["messages"]) > 1
    ]
    if not saved:
        st.caption("No conversations yet.")
    for cid, c in saved:
        col_open, col_del = st.columns([5, 1], vertical_alignment="center")
        is_active = cid == st.session_state.current
        if col_open.button(
            c["title"],
            key=f"open_{cid}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.current = cid
            st.rerun()
        if col_del.button("🗑", key=f"del_{cid}", help="Delete this chat"):
            del st.session_state.chats[cid]
            if is_active:
                new_chat()
            save_chats()
            st.rerun()

    st.divider()
    st.caption(
        "Answers are found with TF-IDF and cosine similarity "
        "(no generative AI involved)."
    )
    st.checkbox("Show matched question and score", key="show_debug")

# ---------- Header ----------
st.title("How can we help?")
st.caption(f"The {BRAND} assistant answers common questions instantly.")

# ---------- Conversation ----------

for msg in messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("source") == "ai":
            st.caption("✨ AI-generated answer. Please confirm anything important with support.")
        if msg.get("matched") and st.session_state.get("show_debug"):
            st.caption(f"Matched: {msg['matched']} (similarity {msg['score']:.2f})")
# ---------- Quick replies (only at the start of a chat) ----------
if len(messages) == 1 and not st.session_state.pending:
    cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        if cols[i % 2].button(suggestion, key=f"sug_{i}", use_container_width=True):
            st.session_state.pending = suggestion
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
            answer, score, matched, source = get_reply(prompt)

        messages.append(
        {"role": "assistant", "content": answer, "matched": matched,
         "score": score, "source": source}
    )
    save_chats()
    st.rerun()