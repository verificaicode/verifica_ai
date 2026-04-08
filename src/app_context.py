import os
import time
from dotenv import load_dotenv
import instaloader
from google import genai
from google.genai.types import GoogleSearch,  Tool
from src.types import PostContent

# Carrega variáveis de ambiente
load_dotenv()

class AppContext():
    def __init__(self):
        # Contém o histórico de mensagens enviadas
        self.posts: dict[str,PostContent] = {}

        # Definição de constantes
        self.TEMP_PATH = "tmp/files"
        self.USERNAME = os.getenv("IG_USERNAME")
        self.PASSWORD = os.getenv("IG_PASSWORD")
        self.API_KEY_GEMINI = os.getenv("API_KEY_GEMINI")
        self.PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
        self.DEBUG = os.getenv("DEBUG") == "true"
        self.VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
        self.VERIFICA_AI_SERVER = os.getenv("VERIFICA_AI_SERVER")
        self.VERIFICA_AI_PROXY = os.getenv("VERIFICA_AI_PROXY")

        start = time.time()

        self.instaloader_context = instaloader.Instaloader(
            filename_pattern="vl_{shortcode}_s1",
            dirname_pattern=self.TEMP_PATH,
            download_videos=True,
            download_video_thumbnails=True,
            download_geotags=False,
            save_metadata=False,
            download_comments=False,
            post_metadata_txt_pattern=''
        )

        if os.path.isfile(f"{os.getcwd()}/tmp/session/{self.USERNAME}"):
            self.instaloader_context.load_session_from_file(self.USERNAME, filename=f"{os.getcwd()}/tmp/session/{self.USERNAME}")  # se já tiver salvo antes
        else:
            self.instaloader_context.login(self.USERNAME, self.PASSWORD)  # Vai fazer o login e manter a sessão
            self.instaloader_context.save_session_to_file(filename=f"{os.getcwd()}/tmp/session/{self.USERNAME}")
        
        print("Instaloader carregado em:", time.time() - start)

        start = time.time()

        self.genai_client = genai.Client(api_key=self.API_KEY_GEMINI)
        self.google_search_tool = Tool(
            google_search = GoogleSearch()
        )

        print("Conexão com LLM feito em:", time.time() - start)

        self.type_fake_name_classes = [
            "🤣 Sátira ou paródia",
            "🤷 Conexão falsa",
            "🎭 Conteúdo enganoso",
            "🗓️ Contexto falso",
            "👀 Conteúdo impostor",
            "✂️ Conteúdo manipulado",
            "🧪 Conteúdo fabricado",
        ]


        self.model = "gemini-2.0-flash"
                
        #models:
            # gemini-1.5-flash
            # gemini-1.5-flash-8b
            # gemini-1.5-pro
            # gemini-2.0-flash
            # gemini-2.0-flash-lite
            # gemini-2.0-flash-preview-image-generation
            # gemini-2.5-flash
            # gemini-2.5-flash-lite
            # gemini-2.5-pro