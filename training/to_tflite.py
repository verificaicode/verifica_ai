import tensorflow as tf

model = tf.keras.models.load_model('is_fact_model.keras')
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Salvar em arquivo
with open('is_fact_model.tflite', 'wb') as f:
    f.write(tflite_model)
