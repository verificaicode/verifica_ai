import joblib
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import pandas as pd
# from nltk.corpus import stopwords

# # Certifique-se de que você já baixou os stopwords do nltk
# import nltk
# nltk.download('stopwords')

# stopwords_pt = stopwords.words('portuguese')

# df2 = pd.read_csv("/content/fit_doc2vec.csv")

# texts2 = df2["texto"]  # ou df.iloc[:, 0] se preferir por índice
# labels2 = df2["id"]      # ou df.iloc[:, 1]

dataset_test = pd.read_csv("../datasets/is_fact_explications.csv")

new_x_test = dataset_test["explication"]  # ou df.iloc[:, 0] se preferir por índice
new_y_test = dataset_test["label"]      # ou df.iloc[:, 1]


df = pd.read_csv("type_fake.csv")

texts = df["text"]  # ou df.iloc[:, 0] se preferir por índice
labels = df["subcategory"]      # ou df.iloc[:, 1]

print("carregado")

param_grid = {
    'hidden_layer_sizes': [
        (50,), (100,), (150,), (200,),
        (100, 50), (150, 75), (200, 100),
        (200, 100, 50)
    ],
    'activation': ['relu', 'tanh'],
    'solver': ['adam', 'sgd'],
    'learning_rate_init': [0.001, 0.01],
    'alpha': [0.0001, 0.001],
    'max_iter': [300]
}

# tagged_data = [TaggedDocument(words=text.lower().split(), tags=[str(i)]) for i, text in enumerate(texts)]

# #75
# tokenizer = Doc2Vec(vector_size=80,  # Tamanho do vetor final
#                 window=5,
#                 min_count=2,
#                 epochs=80,
#                 workers=4,
#                 dm=1,  # distributed memory, melhor para semântica
#                 seed=42)

# tokenizer.build_vocab(tagged_data)

# tokenizer.train(tagged_data, total_examples=tokenizer.corpus_count, epochs=tokenizer.epochs)

# # X = [tokenizer.dv[str(i)] for i in range(len(tagged_data))]
# X = [tokenizer.infer_vector(text.lower().split()) for text in texts]
modelo = Pipeline([
    ("tfidf", TfidfVectorizer(
        lowercase=True,
        ngram_range=(1,2),
        max_features=1500,     # Limita vocabulário (ajuda com poucos dados)
        min_df=2,              # Remove termos muito raros
        stop_words=None  # Remove palavras comuns (se for PT)
      )),  # unigrama + bigrama
    ("svd", TruncatedSVD(n_components=80)),        # reduz dimensão mantendo variância
    ("clf",  MLPClassifier(
        activation="relu",
        alpha=0.0005,
        hidden_layer_sizes=(32,16),
        # learning_rate_init=0.001,
        learning_rate='adaptive',
        max_iter=600,
        solver="adam",
        early_stopping=True,
        validation_fraction=0.1,
        random_state=42
    ))
])

X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)

param_grid = {
    'mlp__hidden_layer_sizes': [(100,50), (200,100,50)],
    'mlp__learning_rate_init': [0.001, 0.005, 0.01],
    'mlp__solver': ['adam', 'sgd'],
    'mlp__alpha': [0.0001, 0.001],
    'mlp__activation': ['relu', 'tanh'],
    'mlp__max_iter': [300, 500]
}
# modelo = MLPClassifier()

# modelo = Pipeline([
#     ('scaler', StandardScaler()),
#     ('mlp', MLPClassifier(activation="relu", alpha=0.0001, hidden_layer_sizes=(16, 8), learning_rate_init=0.001, max_iter=400, solver="adam", random_state=42))
# ])

# grid_search = GridSearchCV(modelo, param_grid, cv=5, scoring='accuracy', verbose=2, n_jobs=-1)
# grid_search.fit(X_train, y_train)
# print("Melhores parâmetros:", grid_search.best_params_)
# print("Melhor score (accuracy):", grid_search.best_score_)
modelo.fit(X_train, y_train)

def predict(phrases):
  print(modelo.predict([phrase.lower() for phrase in phrases]))

predict([
    """A mensagem "o IFPI foi fundado em 11 de setembro de 2001" é **fake**. A análise detalhada e os resultados de pesquisa fornecidos confirmam que a International Federation of the Phonographic Industry (IFPI) foi fundada em **1933**, e não em 2001. A data de 11 de setembro de 2001 não tem nenhuma relação com a fundação da organização. Portanto, a mensagem se encaixa na categoria de **conteúdo fabricado**, pois apresenta uma informação completamente falsa sobre a data de fundação do IFPI. O objetivo, nesse caso, pode ser desinformar ou gerar confusão.""",
    "A imagem, juntamente com a frase sobre o paraquedas, configura um caso de **sátira ou paródia**. A intenção primária não é desinformar, mas sim provocar humor através de uma situação hipotética e exagerada. A frase faz uso de ironia ao sugerir que a falha de um paraquedas acelera a chegada ao ""destino"", quando, na realidade, tal falha pode ter consequências trágicas. As pesquisas corroboram que, embora o paraquedismo tenha seus riscos, há medidas de segurança como o paraquedas reserva. A frase, portanto, deve ser interpretada como uma piada e não como uma informação factual."
])

# y_pred = modelo.predict(x_pred)
# grid_search.fit(X, [rotular(v) for v in confiancas])

y_pred = modelo.predict(X_test)
print(y_test.tolist())
print(y_pred.tolist())
print(classification_report(y_test, y_pred))
# print("Melhores parâmetros:", grid_search.best_params_)
# print("Melhor score (accuracy):", grid_search.best_score_)
# print(accuracy_score([rotular(v) for v in new_confiances], y_pred))

# tokenizer.save("is_fact_tokenizer.model")
joblib.dump(modelo, "../models/type_fake_model.pkl")

# joblib.dump((tokenizer, modelo), os.path.dirname(os.path.abspath(__file__)) + '/is_fact_model.pkl')