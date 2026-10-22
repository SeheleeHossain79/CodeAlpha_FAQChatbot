import json
import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOP_WORDS = set(stopwords.words("english")) - {"not", "no"}
LEMMATIZER = WordNetLemmatizer()

# If the best match scores below this, the bot admits it doesn't know.
THRESHOLD = 0.25


def preprocess(text):
    """Lowercase -> remove punctuation -> tokenize -> remove stop words -> lemmatize."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = word_tokenize(text)
    tokens = [LEMMATIZER.lemmatize(t) for t in tokens if t not in STOP_WORDS]
    return " ".join(tokens)


class FAQChatbot:
    def __init__(self, faq_path="faqs.json"):
        with open(faq_path, encoding="utf-8") as f:
            self.faqs = json.load(f)

        self.questions = [item["question"] for item in self.faqs]
        self.processed = [preprocess(q) for q in self.questions]

        self.vectorizer = TfidfVectorizer()
        self.matrix = self.vectorizer.fit_transform(self.processed)

    def get_answer(self, user_question):
        cleaned = preprocess(user_question)
        if not cleaned.strip():
            return "Please type a question.", 0.0, None

        user_vector = self.vectorizer.transform([cleaned])
        scores = cosine_similarity(user_vector, self.matrix)[0]
        best = int(scores.argmax())
        best_score = float(scores[best])

        if best_score < THRESHOLD:
            return (
                "Sorry, I don't have an answer for that. "
                "Try rephrasing, or contact support@example.com.",
                best_score,
                None,
            )
        return self.faqs[best]["answer"], best_score, self.questions[best]


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