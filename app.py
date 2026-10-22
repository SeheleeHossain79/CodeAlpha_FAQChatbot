import streamlit as st
from chatbot import FAQChatbot

st.set_page_config(page_title="FAQ Chatbot", page_icon="🤖")
st.title("🤖 Shop FAQ Chatbot")
st.caption("Ask me about orders, delivery, returns, payments and more.")


@st.cache_resource
def load_bot():
    return FAQChatbot()


bot = load_bot()

WELCOME = "Hi! 👋 Ask me anything about orders, delivery, returns, or payments."

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME}]


def show_message(msg):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("matched") and st.session_state.get("show_debug"):
            st.caption(f"Matched: {msg['matched']} (similarity {msg['score']:.2f})")


# ---------- Sidebar ----------
with st.sidebar:
    st.header("About")
    st.write(
        "This chatbot matches your question to the most similar FAQ "
        "using TF-IDF and cosine similarity."
    )
    st.checkbox("Show matched question and score", key="show_debug")
    if st.button("Clear chat"):
        st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
        st.rerun()
    st.divider()
    st.subheader("Try asking")
    st.markdown(
        "- Where is my package?\n"
        "- How do I get my money back?\n"
        "- Do you take PayPal?\n"
        "- My parcel arrived broken\n"
        "- Any discount offers?"
    )

# ---------- Chat history ----------
for msg in st.session_state.messages:
    show_message(msg)

# ---------- New message ----------
if prompt := st.chat_input("Type your question here..."):
    user_msg = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_msg)
    show_message(user_msg)

    answer, score, matched = bot.get_answer(prompt)
    bot_msg = {"role": "assistant", "content": answer, "matched": matched, "score": score}
    st.session_state.messages.append(bot_msg)
    show_message(bot_msg)