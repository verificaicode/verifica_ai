import tensorflow as tf
import pandas as pd
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

# Carregar dados
dataset_train = pd.read_csv("../datasets/is_fact.csv")
texts = dataset_train["text"].astype(str)

# Aplicar TfidfVectorizer para capturar vocabulário e pesos
tfidf = TfidfVectorizer(
    lowercase=True,
    ngram_range=(1, 2),
    max_features=1500,
    min_df=2,
    stop_words=None
)
X_tfidf = tfidf.fit_transform(texts)

# Capturar vocabulário
vocab = tfidf.get_feature_names_out()
idf_weights = tfidf.idf_

# Cria camada TextVectorization com vocabulário pronto
vectorizer = tf.keras.layers.TextVectorization(
    max_tokens=len(vocab) + 1,
    output_mode="tf_idf",
    ngrams=2  # gera n-grams como no TfidfVectorizer
)
vectorizer.set_vocabulary(vocab, idf_weights)

# Reduz dimensionalidade com SVD (pré-treinado)
svd = TruncatedSVD(n_components=80, random_state=42)
X_reduced = svd.fit_transform(X_tfidf)

# Captura os componentes e bias
weights = svd.components_.T  # shape: (1500, 80)
bias = -svd.mean_.dot(weights)  # bias para centralização

# Camada densa fixa simulando o SVD
svd_layer = tf.keras.layers.Dense(
    units=80,
    use_bias=False,
    trainable=False,
    name="svd"
)
# Inicializa a camada com os pesos do SVD
svd_layer.build((None, len(vocab)))
svd_layer.set_weights([weights, bias])

# Modelo Keras com TextVectorization + SVD
input_text = tf.keras.Input(shape=(1,), dtype=tf.string)
x = vectorizer(input_text)
x = svd_layer(x)
model = tf.keras.Model(inputs=input_text, outputs=x)

# Salvar modelo exportável
model.save("../models/is_fact_vectorizer_tf", include_optimizer=False)
