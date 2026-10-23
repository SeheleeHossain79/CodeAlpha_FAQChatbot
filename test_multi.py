from chatbot import FAQChatbot

bot = FAQChatbot()
MESSAGES = [
    "hello. I loved one of your product, But another one was recieved broken, so I want to refund it. Can you tell me the refund process? and I also want to give a positive feedback about the product I loved. tell me the feedback process too.",
    "hello, how can I get refund?",
    "good morning",
    "good morning, where is my package and how long does delivery take?",
    "assalamu alaikum",
    "thank you",
]

for message in MESSAGES:
    info = bot.analyze(message)
    print("MESSAGE:", message[:70])
    print("  greeting:", info["greeting"], "| greeting only:", info["greeting_only"])
    for question, score in info["intents"]:
        print(f"  - {question} ({score:.2f})")
    print()