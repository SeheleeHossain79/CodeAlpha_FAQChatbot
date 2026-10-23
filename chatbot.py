import json
import re

import nltk

for package in ("punkt", "punkt_tab", "stopwords"):
    nltk.download(package, quiet=True)

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOP_WORDS = set(stopwords.words("english"))
STEMMER = PorterStemmer()

# If the best match scores below this, the bot does not trust it.
THRESHOLD = 0.25

# ---------- Topics (used by the topic browser and "related questions") ----------
HIDDEN = {"hello", "thank you"}   # small-talk FAQs, not shown in the browser
CATEGORY_ORDER = [
    "Orders", "Delivery", "Payments", "Returns & Refunds",
    "Offers", "Products", "Account & Privacy", "Support",
]
# First rule that matches wins. You can also add  "category": "Delivery"  to any
# entry in faqs.json to set its topic by hand.
CATEGORY_RULES = [
    ("Returns & Refunds", ["return", "refund", "exchange", "damaged", "wrong item",
                           "missing", "warranty", "defective"]),
    ("Payments", ["pay", "card", "cash", "installment", "invoice", "receipt",
                  "vat", "tax", "charged", "deducted", "price", "pending"]),
    ("Delivery", ["deliver", "shipping", "ship", "track", "courier", "express",
                  "international", "bangladesh", "address", "receive"]),
    ("Offers", ["discount", "coupon", "promo", "sale", "arrival", "newsletter",
                "voucher", "wholesale", "bulk"]),
    ("Account & Privacy", ["account", "password", "sign up", "register",
                           "personal information", "safe"]),
    ("Support", ["contact", "support", "feedback", "review", "complaint"]),
    ("Orders", ["order", "cancel", "checkout", "purchase", "buy"]),
    ("Products", ["product", "sell", "stock", "quality", "specification",
                  "original", "gift", "item"]),
]


def get_category(faq):
    if "category" in faq:
        return faq["category"]
    q = faq["question"].lower().strip(" ?!.")
    if q in HIDDEN:
        return None
    for category, words in CATEGORY_RULES:
        if any(w in q for w in words):
            return category
    return "General"


GREETING_RE = re.compile(
    r"^\s*(?:(?:hello|hi|hey|hiya|howdy|salam|assalamu\s+alaikum|assalamualaikum"
    r"|good\s+(?:morning|afternoon|evening|day))(?:\s+there)?\b[\s,.!:;-]*)+",
    re.IGNORECASE,
)
THANKS_RE = re.compile(
    r"[\s,.!;-]*\b(?:thanks|thank\s+you|thx)\b(?:\s+(?:a\s+lot|so\s+much))?[\s.!]*$",
    re.IGNORECASE,
)


def strip_smalltalk(text):
    """Remove a leading greeting and a trailing 'thanks' if a real question remains."""
    cleaned = GREETING_RE.sub("", text, count=1)
    cleaned = THANKS_RE.sub("", cleaned, count=1)
    return cleaned if re.search(r"[A-Za-z0-9]", cleaned) else text

def preprocess(text):
    """Lowercase -> remove punctuation -> tokenize -> remove stop words -> stem."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = word_tokenize(text)
    tokens = [STEMMER.stem(t) for t in tokens if t not in STOP_WORDS]
    return " ".join(tokens)


class FAQChatbot:
    def __init__(self, faq_path="faqs.json"):
        with open(faq_path, encoding="utf-8") as f:
            self.faqs = json.load(f)

        # One row per phrasing: the main question plus every variant.
        # owner[i] remembers which FAQ row i belongs to.
        self.phrasings = []
        self.owner = []
        for idx, item in enumerate(self.faqs):
            for text in [item["question"]] + item.get("variants", []):
                self.phrasings.append(text)
                self.owner.append(idx)

        processed = [preprocess(t) for t in self.phrasings]
        self.vectorizer = TfidfVectorizer()
        self.matrix = self.vectorizer.fit_transform(processed)

        self.answer_of = {f["question"]: f["answer"] for f in self.faqs}
        self.category_of = {f["question"]: get_category(f) for f in self.faqs}

    def get_answer(self, user_question):
        cleaned = preprocess(strip_smalltalk(user_question))
        if not cleaned.strip():
            return "Please type a question.", 0.0, None

        user_vector = self.vectorizer.transform([cleaned])
        scores = cosine_similarity(user_vector, self.matrix)[0]
        best_row = int(scores.argmax())
        best_score = float(scores[best_row])
        faq = self.faqs[self.owner[best_row]]

        if best_score < THRESHOLD:
            return (
                "Sorry, I don't have an answer for that. "
                "Try rephrasing, or contact support@littleaura.com.",
                best_score,
                None,
            )
        return faq["answer"], best_score, faq["question"]

    def suggest(self, user_question, n=3):
        """The n closest FAQs as (question, score), best first."""
        cleaned = preprocess(strip_smalltalk(user_question))
        if not cleaned.strip():
            return []
        user_vector = self.vectorizer.transform([cleaned])
        scores = cosine_similarity(user_vector, self.matrix)[0]

        best = {}  # FAQ index -> best score among its phrasings
        for row, score in enumerate(scores):
            idx = self.owner[row]
            if score > best.get(idx, 0):
                best[idx] = float(score)

        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        results = []
        for idx, score in ranked:
            question = self.faqs[idx]["question"]
            if score > 0 and self.category_of[question]:
                results.append((question, score))
            if len(results) == n:
                break
        return results

    def related(self, question, n=3):
        """Other questions from the same topic."""
        category = self.category_of.get(question)
        if not category:
            return []
        same = [q for q, c in self.category_of.items() if c == category]
        if len(same) <= 1:
            return []
        i = same.index(question)
        count = min(n, len(same) - 1)
        return [same[(i + k) % len(same)] for k in range(1, count + 1)]

    def topics(self):
        """{topic name: [questions]} in a sensible order."""
        groups = {}
        for faq in self.faqs:
            category = self.category_of[faq["question"]]
            if category:
                groups.setdefault(category, []).append(faq["question"])
        ordered = {c: groups[c] for c in CATEGORY_ORDER if c in groups}
        for category in groups:
            ordered.setdefault(category, groups[category])
        return ordered


if __name__ == "__main__":
    bot = FAQChatbot()
    print("FAQ Chatbot ready. Type 'quit' to exit.\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in {"quit", "exit"}:
            break
        answer, score, matched = bot.get_answer(q)
        print(f"Bot: {answer}")
        if matched:
            print(f"     (matched: '{matched}', similarity {score:.2f})\n")
        else:
            print(f"     (best similarity {score:.2f})\n")