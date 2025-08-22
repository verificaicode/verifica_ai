from datetime import datetime
from json.decoder import JSONDecodeError
import traceback
from google.genai.types import File
from verifica_ai.handle_gemini_api import HandleGeminiAPI
from verifica_ai.exceptions import VerificaAiException
from verifica_ai.types import DetalhedFont, PostContent, PostType
from verifica_ai.utils import insert_into_prompt

class Processor():
    """
    Responsável por processar o `PostContent` com a Gemini API e retornar a resposta.

    :param handle_gemini_api: Responsável por gerenciar a API do Gemini.
    :type handle_gemini_api: HandleGeminiAPI
    """

    def __init__(self, handle_gemini_api: HandleGeminiAPI) -> None:
        self.handle_gemini_api = handle_gemini_api

        with open(f"prompts/search_prompt.txt", 'r', encoding='utf-8') as f:
            self.search_prompt = f.read()

        with open(f"prompts/search_prompt_with_reference.txt", 'r', encoding='utf-8') as f:
            self.search_prompt_with_reference = f.read()

        with open(f"prompts/analysis_prompt.txt", 'r', encoding='utf-8') as f:
            self.analysis_prompt = f.read() 

        with open(f"prompts/analysis_prompt_with_reference.txt", 'r', encoding='utf-8') as f:
            self.analysis_prompt_with_reference = f.read() 

    async def get_result(self, post_content: PostContent) -> tuple[str, list[DetalhedFont]]:
        try:
            response = await self.get_gemini_response(post_content)
            return response

        except Exception:
            traceback.print_exc()
            VerificaAiException.InternalError()

    async def get_gemini_response(self, post_content: PostContent) -> tuple[str, list[DetalhedFont]]:
        """
        Processa o contéudo e obtém a resposta pelo Gemini API.

        :param post_content: Contém os dados do conteúdo a ser analisado.

        :return: Uma tupla com a resposta gerada e uma lista contendo `DetalhedFont` 
        """

        post_type = post_content.post_type
        is_media = post_type == PostType.VIDEO or post_type == PostType.IMAGE

        object_if_is_old_message = post_content.object_if_is_old_message
        file = await self.handle_gemini_api.upload_file(post_content.filename) if is_media else None
        post_date = post_content.data.date()
        current_date = datetime.now().date()

        response = None
        fonts = None

        try:
            response, fonts = await self.execute_prompts(post_content, is_media, object_if_is_old_message, file, post_date, current_date)
        
        # Se o erro for causado por uma má formatação de resposta gerada pela pesquisa do Gemini
        except VerificaAiException.ResponseSearchFormatError:
            try:
                response, fonts = await self.execute_prompts(post_content, is_media, object_if_is_old_message, file, post_date, current_date)
            
            # Se der erro novamente, relança para o tratamento de erros principal
            except Exception:
                raise

        self.handle_gemini_api.delete_file() if file else None

        return [ response, fonts ] if fonts else response
        
    async def execute_prompts(self, post_content: PostContent, is_media: bool, object_if_is_old_message, file: File | None, post_date: str, current_date: str):
        try:
            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                prompt_text = insert_into_prompt(
                    self.search_prompt_with_reference,
                    { "label": "CAPTION", "caption": post_content.text or post_content.caption, "text": text }
                )

                prompt_parts = [prompt_text, file]

                search_response, fonts = await self.handle_gemini_api.generate_response(prompt_parts, True)

                prompt_text = insert_into_prompt(
                    self.analysis_prompt_with_reference,
                    { "text": text, "caption": post_content.text or post_content.caption, "search_response": search_response, "post_date": post_date, "current_date": current_date }
                )
                
                prompt_parts = [prompt_text, file]

                response_text, _ = await self.handle_gemini_api.generate_response(prompt_parts)

                return response_text, fonts

            else:
                prompt_text = insert_into_prompt(
                    self.search_prompt,
                    { "label": "CAPTION", "caption": post_content.text or post_content.caption }
                )

                prompt_parts = [prompt_text]

                if is_media:
                    prompt_parts.append(file)

                search_response, fonts = await self.handle_gemini_api.generate_response(prompt_parts, True)

                prompt_text = insert_into_prompt(
                    self.analysis_prompt,
                    { "caption": post_content.text or post_content.caption, "search_response": search_response, "post_date": post_date, "current_date": current_date }
                )
                
                prompt_parts = [prompt_text]

                if is_media:
                    prompt_parts.append(file)

                response_text, _ = await self.handle_gemini_api.generate_response(prompt_parts)

                return response_text, fonts
        
        # Caso o erro seja gerado ao tentar converter para json a resposta da pesquisa processada (retirando o markdown ```json{conteúdo}```)
        except JSONDecodeError:
            raise VerificaAiException.ResponseSearchFormatError()
        
        except Exception:
            traceback.print_exc()
            raise VerificaAiException.InternalError()