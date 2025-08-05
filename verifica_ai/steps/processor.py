import asyncio
from datetime import datetime
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from google.genai import Client
from google.genai.errors import ClientError
from google.genai.types import File, FileState, GenerateContentConfig, GenerateContentResponse, Tool
from verifica_ai.exceptions import VerificaAiException
from verifica_ai.types import DetalhedFont, PostContent, PostType
from verifica_ai.utils import get_final_urls, insert_into_prompt

class Processor():
    def __init__(self, genai_client: Client, model: str, google_search_tool: Tool) -> None:
        self.genai_client = genai_client
        self.model = model
        self.google_search_tool = google_search_tool

        with open(f"prompts/search_prompt.txt", 'r', encoding='utf-8') as f:
            self.search_prompt = f.read()

        with open(f"prompts/search_prompt_with_reference.txt", 'r', encoding='utf-8') as f:
            self.search_prompt_with_reference = f.read()

        with open(f"prompts/analysis_prompt.txt", 'r', encoding='utf-8') as f:
            self.analysis_prompt = f.read() 

        with open(f"prompts/analysis_prompt_with_reference.txt", 'r', encoding='utf-8') as f:
            self.analysis_prompt_with_reference = f.read() 

    async def get_result(self, post_content: PostContent) -> tuple[str, list[DetalhedFont]]:
        return await self.get_gemini_response(post_content)

    async def get_gemini_response(self, post_content: PostContent) -> tuple[str, list[DetalhedFont]]:
        """
        Processa o contéudo e obtém a resposta pelo Gemini API

        :param post_content:
            Contém os dados do conteúdo a ser analisado

        :return: Uma tupla com a resposta gerada e uma lista contendo `DetalhedFont` 
        """
        
        post_type = post_content.post_type
        is_media = post_type == PostType.VIDEO or post_type == PostType.IMAGE

        object_if_is_old_message = post_content.object_if_is_old_message
        file = self.upload_file(post_content.filename) if is_media else None
        post_date = post_content.data.date()
        current_date = datetime.now().date()

        response = None

        if object_if_is_old_message:
            text = object_if_is_old_message["text"]

            prompt_text = insert_into_prompt(
                self.search_prompt_with_reference,
                { "label": "CAPTION", "caption": post_content.caption, "text": text }
            )

            prompt_parts = [prompt_text, file]

            search_response, fonts = await self.generate_response(prompt_parts)

            prompt_text = insert_into_prompt(
                self.analysis_prompt_with_reference,
                { "text": text, "caption": post_content.caption, "search_response": search_response, "post_date": post_date, "current_date": current_date }
            )
            
            prompt_parts = [prompt_text, file]

            response_text, _ = await self.generate_response(prompt_parts)

            response = response_text, fonts

        else:
            prompt_text = insert_into_prompt(
                self.search_prompt,
                { "label": "CAPTION", "caption": post_content.text or post_content.caption }
            )

            prompt_parts = [prompt_text]

            if is_media:
                prompt_parts.append(file)

            search_response, fonts = await self.generate_response(prompt_parts)

            prompt_text = insert_into_prompt(
                self.analysis_prompt,
                { "caption": post_content.caption, "search_response": search_response, "post_date": post_date, "current_date": current_date }
            )
            
            prompt_parts = [prompt_text]

            if is_media:
                prompt_parts.append(file)

            response_text, _ = await self.generate_response(prompt_parts)

            response = response_text, fonts


        self.genai_client.files.delete(name = file.name) if is_media else None

        return response
    
        if post_type == PostType.VIDEO:
            caption = post_content.caption

            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                response_text, fonts = await self.generate_response([
                    f"""Legenda: "{caption}". Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente no video e na legenda. Separe em temas que podem ou não comprovar a veracidade do conteúdo presente na mensagem e e realize pesquisas para cada um deles. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text, _ = await self.generate_response([
                    (
                        f"""Legenda: "{caption}". Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação. A data do conteúdo analisado é: {data}
                        """,
                        self.analysis_prompt
                    ),
                    file
                ])

                response = response_text, fonts

            else:
                response_text, fonts = await self.generate_response([
                    f"""Legenda: "{caption}". Analise detalhadamento o conteúdo presente no video e na legenda. Separe em temas que podem ou não comprovar sua veracidade e realize pesquisas para cada um deles. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text, _ = await self.generate_response([
                    (
                        f"""Legenda: "{caption}". Analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}. A data do conteúdo analisado é: {data}""",
                        self.analysis_prompt
                    ),
                    file
                ])

                response = response_text, fonts

            self.genai_client.files.delete(name = file.name)
    
        elif post_type == PostType.IMAGE:
            caption = post_content.caption
        
            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                response_text, fonts = await self.generate_response([
                    f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Realize pesquisas sobre assuntos que podem ou não comprovar a veracidade do conteúdo presente na mensagem. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text, _ = await self.generate_response([(
                        f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Depois, analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação. A data do conteúdo analisado é: {data}""",
                        self.analysis_prompt
                    ),
                    file
                ])
                
                response = response_text, fonts

            else:
                prompt = insert_into_prompt
                search_response, fonts = await self.generate_response([prompt, file], True)

                prompt = insert_into_prompt(self.analysis_prompt, {
                    "caption": caption,
                    "search_response": search_response,
                    "post_date": post_date,
                    "current_date": current_date
                })

                response_text, _ = await self.generate_response([prompt, file])

                response = response_text, fonts

            self.genai_client.files.delete(name = file.name)
    
        elif post_type == PostType.TEXT:
            text = post_content.text

            response_text, fonts = await self.generate_response((
                f"""Analise detalhadamente a mensagem: "{text}". Realize pesquisas sobre assuntos que podem ou não comprovar sua veracidade. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                """
            ), True)

            response_text, _ = await self.generate_response((
                f"""Analise detalhadamente o conteúdo presente na mensagem "{text}". Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje' e não especificar o contexto como de alguma outra data, analise com base na data previamente fornecida para verificação. A data do conteúdo analisado é: {data}""",
                self.analysis_prompt
            ))
            
            response = response_text, fonts

        return response

    def upload_file(self, filename: str) -> File:
        state = FileState.PROCESSING
        file = self.genai_client.files.upload(file=filename)

        while state != FileState.ACTIVE:
            state = self.genai_client.files.get(name=file.name).state
            asyncio.sleep(0.5)

        os.remove(filename)

        return file
    
    async def split_text_and_fonts(self, response: GenerateContentResponse) -> tuple[str, list[DetalhedFont]]:
        """
        Separa a resposta da LLM entre texto e fontes.

        :param response: Contém a resposta gerada pela LLM.

        :return: Uma tupla contendo o texto e uma lista com `DetalhedFont`.
        """

        text = response.text
        fonts = []
        if response.candidates[0].grounding_metadata:
            if response.candidates[0].grounding_metadata.grounding_chunks:
                fonts = await get_final_urls([chunk.web.uri for chunk in response.candidates[0].grounding_metadata.grounding_chunks ])
            
            elif response.candidates[0].grounding_metadata.search_entry_point:
                html = response.candidates[0].grounding_metadata.search_entry_point.rendered_content
                soup = BeautifulSoup(html, "html.parser")
                
                fonts = await get_final_urls([a["href"] for a in soup.find_all('a', class_='chip')])

        detalhed_fonts = []
        for font in fonts:
            host = urlparse(font).netloc
            detalhed_fonts.append(DetalhedFont(uri=font, domain=host[4:] if host.startswith("www.") else host))
            
        return text, detalhed_fonts
    
    async def generate_response(self, prompt: list[str | File], use_google_search = False) -> tuple[str, list[str]]:
        """
        Executa os prompts e retorna o resultado.

        :param prompt: Prompt a ser executado pelo GEMINI

        :param use_google_search: Se verdadeiro, o prompt fazerá pesquisas na internet
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

                return await self.split_text_and_fonts(generated_content)

            else:
                generated_content = self.genai_client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=GenerateContentConfig(
                            response_modalities=["TEXT"],
                            temperature=0.3
                        )
                )
                return await self.split_text_and_fonts(generated_content)

    
        # Caso algum limite da API foi atingido
        except ClientError as e:
            raise VerificaAiException.GeminiQuotaExceeded(e)