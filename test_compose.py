import tomllib

from chatbot import FAQChatbot
from llm import GeminiFallback

secrets = tomllib.load(open(".streamlit/secrets.toml", "rb"))
bot = FAQChatbot()
ai = GeminiFallback(secrets["GEMINI_API_KEY"], bot.faqs,
                    model=secrets.get("GEMINI_MODEL", "gemini-3-flash-preview"))

message = ("hello. I loved one of your product, But another one was recieved broken, "
           "so I want to refund it. Can you tell me the refund process? and I also want "
           "to give a positive feedback about the product I loved. tell me the feedback "
           "process too.")

info = bot.analyze(message)
facts = [(q, bot.answer_of[q]) for q, _ in info["intents"]]
print("Detected:", [q for q, _ in info["intents"]], "\n")

reply = ai.compose(message, facts, info["greeting"])
print("Finish reason:", ai.last_finish)
print("Token usage:", ai.last_usage)
print("\nREPLY:\n", reply or "(empty: it was cut off, so the app would use the FAQ fallback)")
print("Answered by model:", ai.last_model)