import json
import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

for package in ("punkt", "punkt_tab", "stopwords"):
    nltk.download(package, quiet=True)

STOP_WORDS = set(stopwords.words("english"))
STEMMER = PorterStemmer()

# If the best match scores below this, the bot admits it doesn't know.
THRESHOLD = 0.25


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

    def get_answer(self, user_question):
        cleaned = preprocess(user_question)
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
                "Try rephrasing, or contact support@example.com.",
                best_score,
                None,
            )
        return faq["answer"], best_score, faq["question"]


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