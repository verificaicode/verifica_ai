import os
import eventlet
from google.genai import Client
from google.genai.errors import ClientError
from google.genai.types import File, FileState, GenerateContentConfig, GenerateContentResponse, Tool
from verifica_ai.exceptions import VerificaAiException
from verifica_ai.types import PostContent, PostType
from verifica_ai.utils import get_final_urls
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class Processor():
    def __init__(self, genai_client: Client, model: str, google_search_tool: Tool) -> None:
        self.genai_client = genai_client
        self.model = model
        self.google_search_tool = google_search_tool

        with open(f"prompts/content_categories.txt", 'r', encoding='utf-8') as f:
            self.content_categories = f.read() 

    # Retorna a resposta processada da GEMINI API, fornecendo os prompts necessários para cada tipo de postagem
    def get_result(self, post_content: PostContent) -> str:
        post_type = post_content.post_type
        is_media = post_type == PostType.VIDEO or post_type == PostType.IMAGE

        object_if_is_old_message = post_content.object_if_is_old_message
        file = self.upload_file(post_content.filename) if is_media else None
        data = post_content.data.date()

        response = None
        
        if post_type == PostType.VIDEO:
            caption = post_content.caption

            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                response_text, fonts = self.generate_response([
                    f"""Legenda: "{caption}". Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente no video e na legenda. Separe em temas que podem ou não comprovar a veracidade do conteúdo presente na mensagem e e realize pesquisas para cada um deles. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text, _ = self.generate_response([
                    (
                        f"""Legenda: "{caption}". Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação. A data do conteúdo analisado é: {data}
                        """,
                        self.content_categories
                    ),
                    file
                ])

                response = [ response_text, fonts ]

            else:
                response_text, fonts = self.generate_response([
                    f"""Legenda: "{caption}". Analise detalhadamento o conteúdo presente no video e na legenda. Separe em temas que podem ou não comprovar sua veracidade e realize pesquisas para cada um deles. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text, _ = self.generate_response([
                    (
                        f"""Legenda: "{caption}". Analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}. A data do conteúdo analisado é: {data}""",
                        self.content_categories
                    ),
                    file
                ])

                response = [ response_text, fonts ]

            self.genai_client.files.delete(name = file.name)
    
        elif post_type == PostType.IMAGE:
            caption = post_content.caption
        
            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                response_text, fonts = self.generate_response([
                    f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Realize pesquisas sobre assuntos que podem ou não comprovar a veracidade do conteúdo presente na mensagem. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text, _ = self.generate_response([(
                        f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Depois, analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação. A data do conteúdo analisado é: {data}""",
                        self.content_categories
                    ),
                    file
                ])
                
                response = [ response_text, fonts ]

            else:
                response_text, fonts = self.generate_response([
        f"CAPTION: “{caption}”",
        "Seu objetivo é fazer pesquisas que servirão para determinar a veracidade do conteúdo informado (texto ou legenda (e arquivo, se houver))."
        "1. Separe o conteúdo em temas que podem concluir esse objetivo."
        "2. Para cada tema, realize pesquisas em fontes confiávais.",
        "3. Responda somente com um JSON no seguinte formato:",
        r"""{"tema1": ["resultado de uma pesquisa", "resultado de outra pesquisa"], "tema2": ["..."]}""",
        "Não adicione nenhuma explicação ou comentário fora do JSON.",
                    file
                ], True)

                response_text, _ = self.generate_response([f"""
Você é um verificador de fatos especializado em desinformação. Analise cuidadosamente a legenda, o arquivo (se houver) e o resumo da pesquisa simulada abaixo.

Legenda: "{caption}"
Pesquisa: {response_text}
Data do conteúdo: {data}
Data atual: 03-08-2025

Com base nas evidências e fontes encontradas, classifique a legenda com uma das seguintes categorias, e escreva uma explicação detalhada e contextualizada.
Não escreva menos que 700 caracteres e não ultrapasse 850 caracteres.
Evite termos genéricos como “não há provas”. Foque em explicar *por que* a legenda é enganosa, falsa, fabricada, ou verdadeira, com base nas informações mais relevantes.

Categorias possíveis:
- 🤣 Satira ou paródia
- 🤷 Conexao falsa
- 🎭 Conteudo enganoso
- 🗓️ Contexto falso
- 👀 Conteudo impostor
- ✂️ Conteudo manipulado
- 🧪 Conteudo fabricado
- 🤔 Informacoes insuficientes
- ✅ É fato

Formato da resposta:
<categoria>

<explicação detalhada com base nas evidências>
""",
                    file
                ])

                response = [ response_text, fonts ]

            self.genai_client.files.delete(name = file.name)
    
        elif post_type == PostType.TEXT:
            text = post_content.text

            response_text, fonts = self.generate_response((
                f"""Analise detalhadamente a mensagem: "{text}". Realize pesquisas sobre assuntos que podem ou não comprovar sua veracidade. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                """
            ), True)

            response_text, _ = self.generate_response((
                f"""Analise detalhadamente o conteúdo presente na mensagem "{text}". Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje' e não especificar o contexto como de alguma outra data, analise com base na data previamente fornecida para verificação. A data do conteúdo analisado é: {data}""",
                self.content_categories
            ))
            
            response = [ response_text, fonts ]

        return response

    def upload_file(self, filename: str) -> File:
        state = FileState.PROCESSING
        file = self.genai_client.files.upload(file=filename)

        while state != FileState.ACTIVE:
            state = self.genai_client.files.get(name=file.name).state
            eventlet.sleep(0.5)

        os.remove(filename)

        return file
    
    def split_text_and_fonts(self, response: GenerateContentResponse) -> tuple[str, list[str]]:
        text = response.text
        fonts = []
        if response.candidates[0].grounding_metadata:
            if response.candidates[0].grounding_metadata.grounding_chunks:
                fonts = get_final_urls([chunk.web.uri for chunk in response.candidates[0].grounding_metadata.grounding_chunks ])
            
            elif response.candidates[0].grounding_metadata.search_entry_point:
                html = response.candidates[0].grounding_metadata.search_entry_point.rendered_content
                soup = BeautifulSoup(html, "html.parser")
                
                fonts = get_final_urls([a["href"] for a in soup.find_all('a', class_='chip')])

        detalhed_fonts = []
        for font in fonts:
            host = urlparse(font).netloc
            detalhed_fonts.append({ "uri": font, "domain": host[4:] if host.startswith("www.") else host })
            
        return [ text, detalhed_fonts ]
    
    def generate_response(self, prompt: list[str | File], use_google_search = False) -> tuple[str, list[str]]:
        """
        Executa os prompts e retorna o resultado

        Parâmetros
        ----------
        prompt : list[str | File]
            Prompt a ser executado pelo GEMINI

        use_google_search : boolean, default=False
            Se verdadeiro, o prompt fazerá pesquisas na internet
        """

        try: 
            if use_google_search:
                generated_content = self.genai_client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=GenerateContentConfig(
                        tools=[self.google_search_tool],
                        response_modalities=["TEXT"],
                        temperature=0.0
                    )
                )

                return self.split_text_and_fonts(generated_content)

            else:
                generated_content = self.genai_client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=GenerateContentConfig(
                            response_modalities=["TEXT"],
                            temperature=0.3
                        )
                )
                return self.split_text_and_fonts(generated_content)

    
        # Caso algum limite da API foi atingido
        except ClientError as e:
            raise VerificaAiException.GeminiQuotaExceeded(e)