from datetime import datetime
from verifica_ai.handle_gemini_api import HandleGeminiAPI
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
        file = await self.handle_gemini_api.upload_file(post_content.filename) if is_media else None
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

            search_response, fonts = await self.handle_gemini_api.generate_response(prompt_parts, True)

            prompt_text = insert_into_prompt(
                self.analysis_prompt_with_reference,
                { "text": text, "caption": post_content.caption, "search_response": search_response, "post_date": post_date, "current_date": current_date }
            )
            
            prompt_parts = [prompt_text, file]

            response_text, _ = await self.handle_gemini_api.generate_response(prompt_parts)

            response = response_text, fonts

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
                { "caption": post_content.caption, "search_response": search_response, "post_date": post_date, "current_date": current_date }
            )
            
            prompt_parts = [prompt_text]

            if is_media:
                prompt_parts.append(file)

            response_text, _ = await self.handle_gemini_api.generate_response(prompt_parts)

            response = response_text, fonts

        self.handle_gemini_api.delete_file() if file else None

        return response
