from chatbot import FAQChatbot

bot = FAQChatbot()

# (question a customer might type, the FAQ it SHOULD match; None = bot should say "don't know")
TESTS = [
    ("has my order shipped yet", "How can I track my order?"),
    ("what is the cost of express delivery", "How much does shipping cost?"),
    ("can you deliver to canada", "Do you ship internationally?"),
    ("i want to send back a shirt", "How do I return a product?"),
    ("how long until i am refunded", "How long does a refund take?"),
    ("can i use visa", "What payment methods do you accept?"),
    ("is my credit card safe here", "Is it safe to pay on your website?"),
    ("i cannot remember my password", "I forgot my password. What should I do?"),
    ("how do i sign up", "How do I create an account?"),
    ("i ordered by mistake, can i cancel", "Can I cancel my order?"),
    ("how do i reach support", "How can I contact customer support?"),
    ("do you have any coupons", "Do you offer discounts or coupon codes?"),
    ("my item is broken", "What if I receive a damaged or wrong item?"),
    ("does this come with a warranty", "Do your products have a warranty?"),
    ("hello", "Hello"),
    ("thanks!", "Thank you"),
    # Out-of-scope questions: the bot should admit it doesn't know
    ("what is the capital of france", None),
    ("who won the football match", None),
    ("can you recommend a laptop", None),
    ("tell me a joke", None),
]

correct = 0
failures = []

for question, expected in TESTS:
    _, score, matched = bot.get_answer(question)
    if matched == expected:
        correct += 1
    else:
        failures.append((question, expected, matched, score))

print(f"Accuracy: {correct}/{len(TESTS)} = {correct / len(TESTS):.0%}\n")
for question, expected, matched, score in failures:
    print(f"FAILED: '{question}'")
    print(f"   expected: {expected}")
    print(f"   got:      {matched} (similarity {score:.2f})\n")