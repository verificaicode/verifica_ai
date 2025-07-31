import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline
import joblib

# Carrega o dataset utilizado para treino e validação
dataset_train = pd.read_csv("../datasets/is_fact.csv")
texts = dataset_train["text"]
labels = dataset_train["label"]

# Cria pipeline com TF-IDF e SVD
is_fact_vectorizer = Pipeline([
    ("tfidf", TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        max_features=1500,
        min_df=2,
        stop_words=None
    )),
    ("svd", TruncatedSVD(n_components=80, random_state=42))
])

# Ajusta o pipeline
X_reduced = is_fact_vectorizer.fit_transform(texts)

# Salva o pipeline completo
joblib.dump(is_fact_vectorizer, "../models/is_fact_vectorizer.pkl")