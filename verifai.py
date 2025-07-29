import instaloader
import os
from google import genai
from gensim.models import Doc2Vec
from dotenv import load_dotenv
from google.genai.types import Tool, GoogleSearch
import joblib
import time

# Carrega variáveis de ambiente
load_dotenv()

# models = [
    # gemini-1.5-flash
    # gemini-1.5-flash-8b
    # gemini-1.5-pro
    # gemini-2.0-flash
    # gemini-2.0-flash-lite
    # gemini-2.0-flash-preview-image-generation
    # gemini-2.5-flash-preview-04-17
# ]

class Verifai:
    def __init__(self):
        self.temp_path = "verifica_ai_temp"

        start = time.time()
        self.L = instaloader.Instaloader(
            filename_pattern="vl_{shortcode}",
            dirname_pattern=self.temp_path,
            download_videos=True,
            download_video_thumbnails=True,
            download_geotags=False,
            save_metadata=False,
            download_comments=False,
            post_metadata_txt_pattern=''
        )
        print("Instaloader carregado em:", time.time() - start)

        self.username = os.getenv("IG_USERNAME")
        self.password = os.getenv("IG_PASSWORD")
        self.API_KEY_GEMINI = os.getenv("API_KEY_GEMINI")
        self.PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
        self.DEBUG = os.getenv("DEBUG") == "true"
        self.API_KEY = os.getenv('GOOGLE_API_KEY')
        self.CSE_ID = os.getenv('GOOGLE_CSE_ID')
        self.VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
        self.VERIFICA_AI_SERVER = os.getenv("VERIFICA_AI_SERVER")
        self.VERIFICA_AI_PROXY = os.getenv("VERIFICA_AI_PROXY")

        start = time.time()
        self.client = genai.Client(api_key=self.API_KEY_GEMINI)

        self.google_search_tool = Tool(
            google_search = GoogleSearch()
        )
        print("AIs carregadas em", time.time() - start)

        self.model = "gemini-2.0-flash"

        # start = time.time()
        # self.is_fact_tokenizer = Doc2Vec.load("models/is_fact_tokenizer.model")
        # print("Doc2Vec carregado em", time.time() - start)
        start = time.time()
        self.is_fact_model = joblib.load('models/is_fact_model.pkl')
        print("Joblib carregado em", time.time() - start)

        # type_fake_tokenizer, type_fake_model = joblib.load('models/type_fake_model.pkl')
        self.type_fake_model = joblib.load('models/type_fake_model.pkl')
        self.type_fake_name_classes = [
            "🤣 Sátira ou paródia",
            "🤷 Conexão falsa",
            "🎭 Conteúdo enganoso",
            "🗓️ Contexto falso",
            "👀 Conteúdo impostor",
            "✂️ Conteúdo manipulado",
            "🧪 Conteúdo fabricado",
        ]
