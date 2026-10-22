from chatbot import FAQChatbot

bot = FAQChatbot()

# (customer question, the FAQ it SHOULD match)
TESTS = [
    ("Can I place an order through Facebook or WhatsApp?", "Can I place an order through Facebook or WhatsApp?"),
    ("Can I order multiple products in a single purchase?", "Can I order multiple products in one purchase?"),
    ("Can I request a product that is not listed on your website?", "Can I request a product that is not listed on your website?"),
    ("Will you notify me when an out-of-stock product becomes available?", "Are all products in stock?"),
    ("Do product prices include VAT or other taxes?", "Do product prices include VAT or other taxes?"),
    ("Can I use multiple discount codes on one order?", "How do I use a promo code?"),
    ("How can I apply a promo code at checkout?", "How do I use a promo code?"),
    ("Why is my payment showing as pending?", "Why is my payment showing as pending?"),
    ("What should I do if my payment was deducted but my order was not confirmed?", "What if my payment was deducted but my order was not confirmed?"),
    ("Can I pay in installments?", "Can I pay in installments?"),
    ("Can I schedule my delivery for a specific date?", "Can I schedule my delivery for a specific date?"),
    ("Do you offer express or same-day delivery?", "Do you offer express or same-day delivery?"),
    ("Can someone else receive my order on my behalf?", "Can someone else receive my order for me?"),
    ("What happens if the courier cannot reach me?", "What happens if the courier cannot reach me?"),
    ("Can I inspect the product before accepting delivery?", "Can I inspect the product before accepting delivery?"),
    ("What should I do if my package is missing an item?", "What if I receive a damaged or wrong item?"),
    ("Can I return a product without its original packaging?", "Can I return a product without its original packaging?"),
    ("Are sale or discounted products eligible for returns?", "Are sale or discounted products eligible for returns and exchanges?"),
    ("Can I exchange a product purchased during a sale?", "Are sale or discounted products eligible for returns and exchanges?"),
    ("Do you provide digital invoices or receipts?", "Do you provide digital invoices or receipts?"),
    ("Can I purchase products as gifts for someone else?", "Can I buy a gift, and do you offer gift wrapping?"),
    ("Do you offer gift wrapping or personalized packaging?", "Can I buy a gift, and do you offer gift wrapping?"),
    ("Do you provide wholesale pricing for bulk orders?", "Do you offer wholesale pricing for bulk orders?"),
    ("How can I share feedback or report a complaint?", "How can I give feedback or leave a review?"),
    ("How can I stay updated about new arrivals and upcoming sales?", "How can I stay updated about new arrivals and sales?"),
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
    print(f"   got:      {matched}")
    print(f"   similarity {score:.2f}\n")