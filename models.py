import platform
import joblib
import time
import numpy as np

os_type = platform.system()


if os_type == "Windows":
    from tensorflow._api.v2.lite import Interpreter
    print("Usando TensorFlow (Windows)")
else:
    try:
        from tflite_runtime.interpreter import Interpreter
        print("Usando TFLite Runtime (Linux/macOS)")
    except ImportError:
        print("Erro: tflite_runtime não está instalado.")

class Models():
    def __init__(self):
        start = time.time()
        
        self.is_fact_model = Interpreter(model_path="models/is_fact_model.tflite")
        self.is_fact_model.allocate_tensors()
        self.input_details = self.is_fact_model.get_input_details()
        self.output_details = self.is_fact_model.get_output_details()


        #Carrega modelo que classifica entre os tipos de não fato
        self.is_fact_vectorizer = joblib.load("models/is_fact_vectorizer.pkl")

        print("Modelos carregados em:", time.time() - start)

    def is_fact_predict(self, phrase):
        data_vectorized = self.is_fact_vectorizer.transform([phrase]).astype('float32')
        self.is_fact_model.set_tensor(self.input_details[0]['index'], data_vectorized)
        self.is_fact_model.invoke()
        return int(np.argmax(self.is_fact_model.get_tensor(self.output_details[0]['index'])[0]))

    def type_fake_predict(self, phrase):
        return int(self.type_fake_predict([phrase])[0])

def load_models():

    
    start = time.time()
    is_fact_model = platform.system()
    is_fact_model = joblib.load('models/is_fact_model.pkl')
    print("Joblib carregado em", time.time() - start)

    # type_fake_tokenizer, type_fake_model = joblib.load('models/type_fake_model.pkl')
    type_fake_model = joblib.load('models/type_fake_model.pkl')
    return is_fact_model, is_fact_vectorizer, type_fake_model