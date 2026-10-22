from chatbot import FAQChatbot

bot = FAQChatbot()

# (customer question, the FAQ it SHOULD match)
TESTS = [
    ("What products do you sell?", "What products do you sell?"),
    ("How can I place an order?", "How can I place an order?"),
    ("Do I need to create an account to shop?", "Do I need an account to shop?"),
    ("Are all products currently in stock?", "Are all products in stock?"),
    ("How can I check product details and specifications?", "How can I see product details and specifications?"),
    ("Are your products original and authentic?", "Are your products original and good quality?"),
    ("What payment methods do you accept?", "What payment methods do you accept?"),
    ("Do you offer Cash on Delivery (COD)?", "Do you offer Cash on Delivery (COD)?"),
    ("Do you offer any discounts or special promotions?", "Do you offer discounts or coupon codes?"),
    ("Is there a minimum order amount?", "Is there a minimum order amount?"),
    ("How much does delivery cost?", "How much does shipping cost?"),
    ("How long does delivery take?", "How long does delivery take?"),
    ("Do you deliver all over Bangladesh?", "Do you deliver all over Bangladesh?"),
    ("Can I track my order?", "How can I track my order?"),
    ("Can I change my delivery address after placing an order?", "Can I change my delivery address after placing an order?"),
    ("Can I cancel my order after confirmation?", "Can I cancel my order?"),
    ("What is your return and exchange policy?", "What is your return policy?"),
    ("What should I do if I receive a damaged or incorrect product?", "What if I receive a damaged or wrong item?"),
    ("How long does it take to receive a refund?", "How long does a refund take?"),
    ("Can I exchange a product for a different size or color?", "Can I exchange a product for a different size or color?"),
    ("Do your products come with a warranty?", "Do your products have a warranty?"),
    ("What should I do if a product is out of stock?", "Are all products in stock?"),
    ("Is my personal information safe with your shop?", "Is my personal information safe?"),
    ("How can I contact customer support?", "How can I contact customer support?"),
    ("Do you offer special discounts for regular customers?", "Do you offer discounts or coupon codes?"),
]

correct = 0
failures = []

for question, expected in TESTS:
    _, score, matched = bot.get_answer(question)
    ok = matched == expected
    correct += ok
    print(f"{'PASS' if ok else 'FAIL'}  {question}")
    if not ok:
        failures.append((question, expected, matched, score))

print(f"\nScore: {correct}/{len(TESTS)} = {correct / len(TESTS):.0%}\n")
for question, expected, matched, score in failures:
    print(f"FAILED: '{question}'")
    print(f"   expected: {expected}")
    print(f"   got:      {matched} (similarity {score:.2f})\n")