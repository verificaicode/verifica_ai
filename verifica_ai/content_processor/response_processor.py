import traceback
from verifica_ai.schemas.structures import PostContent
from verifica_ai.schemas.types import PostType

class ResponseProcessor:
    def __init__(self, client, models, content_categories, type_fake_name_classes):
        self.client = client
        self.models = models
        self.content_categories = content_categories
        self.type_fake_name_classes = type_fake_name_classes

    def get_text_from_prompt(self, response):
        if len(response.candidates) > 0 and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            fonts = [chunk.web.uri for chunk in response.candidates[0].grounding_metadata.grounding_chunks]
            text = "".join(part.text for part in response.candidates[0].content.parts)
            return [text, self.get_final_urls(fonts)]
        return response.text

    def process_response(self, response_text: str, fonts: list[str]) -> str:
        formated_fonts = "Fontes:\n" + "\n\n".join(fonts)
        if len(f"{response_text}\n{formated_fonts}") <= 960:
            return f"{response_text}\n{formated_fonts}"
        else:
            if fonts:
                fonts.pop()
                return self.process_response(response_text, fonts)
            else:
                return response_text

    def get_result_from_process(self, post_content: PostContent) -> None:
        # Lógica de análise e geração da resposta final, chamando a Gemini, classificadores e formatando
        # Essa parte pode ser adaptada conforme a sua implementação atual
        try:
            # Se for imagem ou video
            if post_content.post_type == PostType.IMAGE or post_content.post_type == PostType.VIDEO:
                # Retorna o nome do arquivo
                post_content.filename = self.process_content(post_content)

                return self.get_gemini_response(post_content)

            # Se for texto
            else:
                return self.get_gemini_response(post_content)

        except Exception as e:
            print(e)
            traceback.print_exc()
