import streamlit as st
from chatbot import FAQChatbot

st.set_page_config(page_title="Help Assistant", page_icon="💬")

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
        background-color: #E6EEE9;          /* assistant: soft sage */
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background-color: #EFE7DA;          /* customer: soft sand */
    }

    /* Quick-reply buttons */
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

    /* Message input */
    [data-testid="stChatInput"] {border-radius: 18px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_bot():
    return FAQChatbot()


bot = load_bot()

WELCOME = (
    "Hi there! 👋 I'm happy to help. "
    "Ask me about orders, delivery, returns or payments, or pick a topic below."
)
SUGGESTIONS = [
    "Track my order",
    "Return an item",
    "Payment methods",
    "Contact support",
]

st.session_state.setdefault("messages", [{"role": "assistant", "content": WELCOME}])
st.session_state.setdefault("pending", None)


def add_exchange(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    answer, score, matched = bot.get_answer(prompt)
    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "matched": matched, "score": score}
    )


# ---------- Sidebar ----------
with st.sidebar:
    st.header("About")
    st.write(
        "This assistant finds the FAQ most similar to your question "
        "using TF-IDF and cosine similarity."
    )
    st.checkbox("Show matched question and score", key="show_debug")
    if st.button("Start a new chat"):
        st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
        st.session_state.pending = None
        st.rerun()

# ---------- Header ----------
st.title("💬 How can we help?")
st.caption("Our assistant answers common questions instantly.")

# ---------- Conversation ----------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("matched") and st.session_state.get("show_debug"):
            st.caption(f"Matched: {msg['matched']} (similarity {msg['score']:.2f})")

# ---------- Quick replies (only before the first question) ----------
if len(st.session_state.messages) == 1:
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
    add_exchange(prompt)
    st.rerun()