import asyncio
import json
import os
from urllib.parse import urlparse
import traceback
from google.genai import Client
from google.genai.errors import ClientError
from verifica_ai.exceptions import VerificaAiException
from google.genai.types import File, FileState, GenerateContentConfig, GenerateContentResponse, Tool
from verifica_ai.verifica_ai.verifai_types import DetalhedFont
from verifica_ai.utils import get_final_urls

class HandleGeminiAPI:
    """
    Camada responsável por lidar diretamente com a API Gemini.

    :param genai_client: Cliente da API do Gemini.
    :type genai_client: Client

    :param model: Modelo a ser utilizado.
    :type model: str

    :param google_search_tool: Configurações da API de Pesquisa do Google.
    :type google_search_tool: Tool
    """

    def __init__(self, genai_client: Client, model: str, google_search_tool: Tool):
        self.genai_client =  genai_client
        self.model = model
        self.google_search_tool = google_search_tool
        

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
        
    async def split_text_and_fonts(self, response: GenerateContentResponse) -> tuple[str, list[DetalhedFont]]:
        """
        Separa a resposta da LLM entre texto e fontes.

        :param response: Contém a resposta gerada pela LLM.

        :return: Uma tupla contendo o texto e uma lista com `DetalhedFont`.
        """

        text = response.text
        detalhed_fonts = []
        if text.startswith("```"):
            # Carrega o json após remover o ```json e o ```
            search_dict = json.loads(text[8:-4])

            fonts = await get_final_urls(search_dict["urls"])
            
            for font in fonts:
                host = urlparse(font).netloc
                detalhed_fonts.append(DetalhedFont(uri=font, domain=host[4:] if host.startswith("www.") else host))

        return text, detalhed_fonts
    
    async def upload_file(self, filename: str) -> File:
        state = FileState.PROCESSING
        self.file = self.genai_client.files.upload(file=filename)

        while state != FileState.ACTIVE:
            state = self.genai_client.files.get(name=self.file.name).state
            await asyncio.sleep(0.5)

        os.remove(filename)

        return self.file
    
    def delete_file(self):
        self.genai_client.files.delete(name = self.file.name)
        
