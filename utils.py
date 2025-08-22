import asyncio
from datetime import datetime
from urllib.parse import parse_qs, urlparse
import urllib3
import httpx
import traceback
from verifica_ai.types import PostType
import requests
from verifica_ai.exceptions import VerificaAiException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_shortcode_from_url(url: str) -> str:
    """
    Extrai o shortcode (identificador único de uma postagem no Instagram) a partir de uma URL.

    :param url: URL da postagem do Instagram da qual o shortcode será extraído.

    :return: Shortcode da postagem extraído da URL.
    
    Examples
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

    :param url: URL utilizada para extrair o img_index.
    
    :return: Retorna o img_index obtido.

    Examples
    -------
    >>> get_img_index_from_url("https://www.instagram.com/p/ABC123xyz?img_index=3")
    3
    """

    query = parse_qs(urlparse(url).query)
    img_index = int(query.get("img_index", ["1"])[0])

    return img_index

async def get_final_urls(font_urls: list[str]) -> list[str]:
    """
    Segue redirecionamentos HTTP e retorna a URL final de cada fonte.

    :param font_urls: Lista de URLs de fontes (ou arquivos) a serem verificadas.

    :return: Lista com as URLs finais após redirecionamento (ou mensagens de erro).

    :raise VerificaAiException.InternalError: Erro interno ao executar a função

    Examples
    -------
    >>> get_final_urls([
    ...     "https://bit.ly/3GdX7rK",                # → https://www.python.org
    ...     "https://tinyurl.com/2p8bz9z4",          # → https://www.wikipedia.org
    ])
    ['https://www.python.org', 'https://www.wikipedia.org']
    """

    results = requests.post("https://worker.verifai.workers.dev/get_final_urls", headers={ "Content-Type": "application/json" }, json=font_urls).json()

    return results

async def handle_reel_info(url: str) -> tuple[datetime, PostType]:
    """
    Extrai informações do reel.

    :param url: URL da mídia

    :return: Retorna uma tupla contendo um `datetime` com a data de publicação do reel e `PostType` com o tipo do reel (imagem ou vídeo).

    Examples
    -------
    >>> await handle_reel_info("https://www.instagram.com/123456789.mp4")
    (datetime(2025, 8, 3, 12, 0), PostType.VIDEO)
    """

    async with httpx.AsyncClient() as client:
        response = await client.head(url)

    # Obtem a data de publicação do reel
    date_str = response.headers.get('Last-Modified')
    if not date_str:
        date_str = response.headers.get('Date')

    # Obtem o tipo do reel
    content_type = response.headers.get("Content-Type", "").lower()

    post_type = PostType.VIDEO if "video" in content_type else PostType.IMAGE

    return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT"), post_type

def insert_into_prompt(prompt: str, values: dict[str, str]) -> str:
    """
    Insere dados no prompt.

    :param prompt: Prompt que receberá os dados.

    :param values: Valores a serem adicionados no prompt.

    :return: O novo prompt com os dados inseridos.

    Exemplo
    -------
    >>> insert_into_prompt(
    ...     "Hoje é {data_atual}, qual a data de amanhã?",
    ...     { "data_atual": "05 de agosto de 2025" }
    )
    'Hoje é 05 de agosto de 2025, qual a data de amanhã?'
    """

    return prompt.format(**values)