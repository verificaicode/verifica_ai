import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

# Conversão de rótulos para one-hot (3 classes
from tensorflow.keras.utils import to_categorical

from tensorflow.keras.regularizers import l2
from tensorflow.keras.optimizers import Adam

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pandas as pd
import numpy as np
import joblib

# Carrega o modelo de vetorização
pipeline = joblib.load("../models/is_fact_vectorizer.pkl")

# Carrega os datasets utilizados para treino e validação
dataset_train = pd.read_csv("../datasets/is_fact.csv")
dataset_test = pd.read_csv("../datasets/is_fact_explications.csv")

texts = dataset_train["text"]
labels = dataset_train["label"].values  # Já são números: 0, 1, 2
new_x_test = dataset_test["explication"].dropna().astype(str).tolist()  # ou df.iloc[:, 0] se preferir por índice
new_y_test = dataset_test["label"]      # ou df.iloc[:, 1]

X_reduced = pipeline.transform(texts)
y_categorical = to_categorical(labels)

# Divisão treino/teste
X_train, X_test, y_train, y_test = train_test_split(X_reduced, y_categorical, test_size=0.2, random_state=42)

# Modelo Keras (MLP)
model = Sequential([
    Dense(64, activation='relu', input_shape=(80,), kernel_regularizer=l2(0.001)),
    Dropout(0.4),
    Dense(48, activation='relu', kernel_regularizer=l2(0.001)),
    Dropout(0.4),
    Dense(3, activation='softmax')
])

model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy'],  
)

# Treinamento com early stopping
early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

model.fit(
    X_train,
    y_train,
    validation_split=0.1,
    epochs=100,
    batch_size=32,
    callbacks=[early_stop],
    verbose=0
)

# Avaliação
y_pred = model.predict(X_test)
y_pred_labels = np.argmax(y_pred, axis=1)
y_test_labels = np.argmax(y_test, axis=1)

print(classification_report(y_test_labels, y_pred_labels, target_names=["fake", "indeterminate", "fact"]))

y_pred = model.predict(pipeline.transform(new_x_test))
y_pred_labels2 = np.argmax(y_pred, axis=1)
print(new_y_test.tolist())
print(y_pred_labels2.tolist())
print(classification_report(new_y_test, y_pred_labels2))

# Salva modelo em tflite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('is_fact_model.tflite', 'wb') as f:
    f.write(tflite_model)