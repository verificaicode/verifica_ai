from google.genai.errors import ClientError
from google.genai.types import GenerateContentConfig
import requests

from verifica_ai.exceptions import VerificaAiException
from verifica_ai.schemas.structures import PostContent, PostType
from verifica_ai.content_processor.uploader import Uploader


class GeminiResponseGenerator():
    # Executa os prompts e retorna o resultado
    def generate_response(self, prompt, use_google_search = False):
        """
            Executa os prompts e retorna o resultado

            Parâmetros
            ----------
            prompt : str
                Prompt a ser executado pelo GEMINI

            use_google_search : boolean, padrão=Falso
                Se verdadeiro, o prompt fazerá pesquisas na internet
        """

        try: 
            if use_google_search:
                generated_content = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                        config=GenerateContentConfig(
                        tools=[self.google_search_tool],
                        response_modalities=["TEXT"],
                    )
                )
                response = self.get_text_from_prompt(generated_content)

                return [  response, "" ] if (isinstance(response, str)) else response

            generated_content = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
            )
            response = self.get_text_from_prompt(generated_content)
            return [  response, "" ] if (isinstance(response, str)) else response
    
        # Caso algum limite da API foi atingido
        except ClientError as e:
            raise VerificaAiException.GeminiQuotaExceeded(e)

    # Retorna a resposta processada da GEMINI API, fornecendo os prompts necessários para cada tipo de postagem
    def get_gemini_response(self, uploader: Uploader, post_content: PostContent) -> str:
        post_type = post_content.post_type
        is_media = post_type == PostType.VIDEO or post_type == PostType.IMAGE

        object_if_is_old_message = post_content.object_if_is_old_message
        file = uploader.upload_file(post_content.filename) if is_media else None
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

                response_text,_ = self.generate_response([
                    (
                        f"""Legenda: "{caption}". Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação. A data do conteúdo analisado é: {data}
                        """,
                        self.content_categories
                    ),
                    file
                ])
        
            else:
                response_text, fonts = self.generate_response([
                    f"""Legenda: "{caption}". Analise detalhadamento o conteúdo presente no video e na legenda. Separe em temas que podem ou não comprovar sua veracidade e realize pesquisas para cada um deles. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text,_ = self.generate_response([
                    (
                        f"""Legenda: "{caption}". Analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}. A data do conteúdo analisado é: {data}""",
                        self.content_categories
                    ),
                    file
                ])

            self.client.files.delete(name = file.name)

            response = self.process_response(response_text, fonts)
    
        elif post_type == PostType.IMAGE:
        
            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                response_text, fonts = self.generate_response([
                    f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Realize pesquisas sobre assuntos que podem ou não comprovar a veracidade do conteúdo presente na mensagem. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text,_ = self.generate_response([(
                        f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Depois, analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação. A data do conteúdo analisado é: {data}""",
                        self.content_categories
                    ),
                    file
                ])

            else:
                response_text, fonts = self.generate_response([
                    f"""Analise detalhadamente o conteúdo presente na imagem. Realize pesquisas sobre assuntos que podem ou não comprovar sua veracidade. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text,_ = self.generate_response([
                    (
                        f"""Analise detalhadamente o conteúdo presente na imagem. Depois analise os seguintes resultados de pesquisa: "{response_text}". A data do conteúdo analisado é: {data}""",
                        self.content_categories
                    ),
                    file
                ])

            self.client.files.delete(name = file.name)
            response = self.process_response(response_text, fonts)
    
        elif post_type == PostType.TEXT:
            text = post_content.text

            response_text, fonts = self.generate_response((
                f"""Analise detalhadamente a mensagem: "{text}". Realize pesquisas sobre assuntos que podem ou não comprovar sua veracidade. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                """
            ), True)

            response_text,_ = self.generate_response((
                f"""Analise detalhadamente o conteúdo presente na mensagem "{text}". Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje' e não especificar o contexto como de alguma outra data, analise com base na data previamente fornecida para verificação. A data do conteúdo analisado é: {data}""",
                self.content_categories
            ))
            
            response = self.process_response(response_text, fonts)

        parcial_response, fonts = response.split("Fontes:") if "Fontes:" in response else [response, ""]
        # parcial_response = parcial_response.split("É fato")[1] if "É fato" in parcial_response else parcial_response.split("É fake")[1] if "É fake" in parcial_response else parcial_response


        # x = [self.is_fact_tokenizer.infer_vector(parcial_response.lower().split())]

        # return f"{parcial_response}{fonts}"

        classe = self.models.is_fact_predict(parcial_response)
        print(classe)
        if classe == 2:
            return f"✅ É fato\n\n{parcial_response}{fonts}"
        
        elif classe == 1:
            return f"🤔 Informações insuficientes\n\n{parcial_response}{fonts}"
        
        else:
            type_fake_class = self.type_fake_name_classes[self.models.type_fake_predict(parcial_response)]
            return f"{type_fake_class}\n\n{parcial_response}{fonts}"
