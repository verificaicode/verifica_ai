from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import parse_qs, urlparse
import urllib3
import requests
from verifica_ai.types import PostType

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_shortcode_from_url(url: str) -> str:
    """
    Extrai o shortcode (identificador único de uma postagem no Instagram) a partir de uma URL.

    Parâmetros
    ----------
    url : str
        URL da postagem do Instagram da qual o shortcode será extraído.

    Retorna
    -------
    str
        Shortcode da postagem extraído da URL.
    
    Exemplo
    -------
    >>> get_shortcode_from_url("https://www.instagram.com/p/ABC123xyz/")
    'ABC123xyz'
    """
    url = url.split("?")[0]
    shortcode = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]

    return shortcode

def get_img_index_from_url(url: str) -> int:
    """
    Extrai o parâmetro img_index de uma url

    Parâmetros
    ----------
    url : str
        URL utilizada para extrair o img_index.
    
    Retorna
    -------
    int
        Retorna o img_index obtido.

    Exemplo
    -------
    >>> get_img_index_from_url("https://www.instagram.com/p/ABC123xyz?img_index=3")
    3
    """

    query = parse_qs(urlparse(url).query)
    img_index = int(query.get("img_index", ["1"])[0])

    return img_index

def get_final_urls(font_urls: list[str]) -> list[str]:
    """
    Segue redirecionamentos HTTP e retorna a URL final de cada fonte.

    Parâmetros
    ----------
    font_urls : list of str
        Lista de URLs de fontes (ou arquivos) a serem verificadas.

    Retorna
    -------
    list of str
        Lista com as URLs finais após redirecionamento (ou mensagens de erro).

    Exemplo
    -------
    >>> get_final_urls([
    ...     "https://bit.ly/3GdX7rK",                # → https://www.python.org
    ...     "https://tinyurl.com/2p8bz9z4",          # → https://www.wikipedia.org
    ])
    ['https://www.python.org', 'https://www.wikipedia.org']
    """

    def fetch_url(url: str) -> str:
        try:
            response = requests.get(url, allow_redirects=True, verify=False, timeout=10)
            return response.url
        except Exception as e:
            return f"Erro: {e}"

    with ThreadPoolExecutor() as executor:
        final_urls = list(executor.map(fetch_url, font_urls))

    return final_urls

def handle_reels_info(url: str) -> tuple[datetime, PostType]:
    """
    Extrai a data de publicação do reel e seu tipo (imagem ou video).

    Parâmetros
    ----------
    url : str
        URL da mídia

    Retorna
    -------
    tuple[datetime, PostType]

    Exemplo
    -------
    >>> handle_reels_info("https://www.instagram.com/123456789.mp4")
    (datetime<03-08-2025>, PostType.VIDEO)
    """

    response = requests.head(url)

    # Obtem a data de publicação do reel
    date_str = response.headers.get('Last-Modified')
    if not date_str:
        date_str = response.headers.get('Date')

    # Obtem o tipo do reel
    content_type = response.headers.get("Content-Type", "").lower()

    post_type = PostType.VIDEO if "video" in content_type else PostType.IMAGE

    return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT"), post_type