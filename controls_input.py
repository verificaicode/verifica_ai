import requests
import os
import instaloader
from instaloader import BadResponseException
import time
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig
from google.genai.errors import ClientError
from exceptions import VerificaAiException
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

posts = {}

class ControlsInput():
    def __init__(self):
        with open(f"prompts/content_categories.txt", 'r', encoding='utf-8') as f:
            self.content_categories = f.read() 

    # Envia o arquivo do post (imagem/video) para o servidor da GEMINI API
    def upload_file(self, filename):
        file = self.client.files.upload(file = filename)

        state = genai.types.FileState.PROCESSING
        while state == genai.types.FileState.PROCESSING:
            state = self.client.files.get(name = file.name).state
            time.sleep(1)

        return file
    
    def get_fonts_url_after_redirect(self, fonts: list):
        def fetch_url(url):
            try:
                response = requests.get(url, allow_redirects=True, verify=False, timeout=10)
                return response.url
            except Exception as e:
                return f"Erro: {e}"

        with ThreadPoolExecutor() as executor:
            converted_fonts = list(executor.map(fetch_url, fonts))

        return converted_fonts
    
    # Extrai o texto (e as fontes caso necessário) do objeto de resposta retornado da GEMINI API
    def get_text_from_prompt(self, response):
        if len(response.candidates) > 0 and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            fonts = []
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                fonts.append(chunk.web.uri)
            text = ""
            for part in response.candidates[0].content.parts:
                text += part.text

            return [ text, self.get_fonts_url_after_redirect(fonts) ]
        
        return response.text

    def get_shortcode_from_url(self, url):
        url = url.split("?")[0]
        return url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]

    # Garante que a resposta não ultrapasse 960 caracteres, removendo fontes até diminuir o suficiente
    def process_response(self, response_text: str, fonts: list):
        formated_fonts = "Fontes:\n" + "\n\n".join(fonts)

        if len(f"{response_text}\n{formated_fonts}") <= 960:
            return f"{response_text}\n{formated_fonts}"
        else:
            if len(fonts) > 0:
                fonts.pop()
                return self.process_response(response_text, fonts)
            else:
                return response_text

    # Processa o conteudo do link e retorna o tipo do link e retorna o nome do arquivo baixado e o tipo dele
    def process_content(self, content):
        is_shared_reel = content["is_shared_reel"]

        try:  
            shortcode = content["shortcode"]

            # Se for uma postagem compartilhada pelo aplicativo do tipo video ou um video enviado pela galeria
            if is_shared_reel or ("type" in content and content["type"] == "video"):
                response = requests.get(content["file_src"], stream=True)
                filename = None
                if content["type"] == "video":
                    filename = f"{self.temp_path}/v_{str(shortcode)}.mp4"
                else:
                    filename = f"{self.temp_path}/v_{str(shortcode)}.jpg"

                with open(filename, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                if content["type"] == "video":
                    return [ filename, "video" ]
                else:
                    return [ filename, "image" ]
                
            else:               
                self.L.download_post(content["post"], target="verifica_ai_temp")

                if content["post"].is_video:
                    filename = f"{self.temp_path}/vl_{shortcode}.mp4"
                    return [ filename, "video" ]
                else:
                    filename = f"{self.temp_path}/vl_{shortcode}.jpg"
                    return [ filename, "image" ]

        except Exception as e:
            print(e)

    # Envia a mensagem para o usuário
    def send_message_to_user(self, user_id, message_text):
        url = f"https://graph.instagram.com/v22.0/me/messages"
        payload = {
            "messaging_product": "instagram",
            "recipient": {"id": user_id},
            "message": {"text": message_text}
        }
        headers = {
            "Authorization": f"Bearer {self.PAGE_ACCESS_TOKEN}"
        }
        v = requests.post(url, headers=headers, json=payload).json()

        # Verifica se ocorreu um erro ao tentar enviar a mensagem.
        if "error" in v:
            raise VerificaAiException.GraphAPIError(v)

    # Executa os prompts e retorna o resultado
    def generate_response(self, prompt, use_google_search = False):
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
    
        except ClientError as e:
            raise VerificaAiException.GeminiQuotaExceeded(e)
    
    def get_uploaded_file(self, content):
            filename = content["filename"]
            file = self.upload_file(filename)
            os.remove(filename)

            return file

    # Retorna a resposta processada da GEMINI API, fornecendo os prompts necessários para cada tipo de postagem
    def get_response_from_type(self, type, content):
        is_media = type == "video" or type == "image"

        object_if_is_old_message = content["object_if_is_old_message"] if "object_if_is_old_message" in content else None
        file = self.get_uploaded_file(content) if is_media else None

        
        if type == "video":
            caption = content["caption"]

            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                response_text, fonts = self.generate_response([
                    f"""Legenda: "{caption}". Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente no video e na legenda. Separe em temas que podem ou não comprovar a veracidade do conteúdo presente na mensagem e e realize pesquisas para cada um deles. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text,_ = self.generate_response([
                    (
                        f"""Legenda: "{caption}". Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação.
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
                        f"""Legenda: "{caption}". Analise detalhadamente o conteúdo presente no video e na legenda. Depois analise os seguintes resultados de pesquisa: "{response_text}".""",
                        self.content_categories
                    ),
                    file
                ])

            self.client.files.delete(name = file.name)

            return self.process_response(response_text, fonts)
    
        elif type == "image":
        
            if object_if_is_old_message:
                text = object_if_is_old_message["text"]

                response_text, fonts = self.generate_response([
                    f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Realize pesquisas sobre assuntos que podem ou não comprovar a veracidade do conteúdo presente na mensagem. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                    """,
                    file
                ], True)

                response_text,_ = self.generate_response([(
                        f"""Segundo a mensagem "{text}", analise detalhadamente o conteúdo presente na imagem. Depois, analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje', considere a data previamente fornecida para verificação.""",
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
                        f"""Analise detalhadamente o conteúdo presente na imagem. Depois analise os seguintes resultados de pesquisa: "{response_text}".
                        """,
                        self.content_categories
                    ),
                    file
                ])

            self.client.files.delete(name = file.name)
            return self.process_response(response_text, fonts)
    
        elif type == "text":
            text = content["text"]

            response_text, fonts = self.generate_response((
                f"""Analise detalhadamente a mensagem: "{text}". Realize pesquisas sobre assuntos que podem ou não comprovar sua veracidade. Busque sempre os mais recentes. Se o conteúdo for temporal, busque sobre ele em si. Retorne no final, a data de hoje (considerando horário de Brasilia).
                """
            ), True)

            response_text,_ = self.generate_response((
                f"""Analise detalhadamente o conteúdo presente na mensagem "{text}". Depois analise os seguintes resultados de pesquisa: "{response_text}". Se a mensagem conter 'hoje' e não especificar o contexto como de alguma outra data, analise com base na data previamente fornecida para verificação.
                """,
                self.content_categories
            ))
            
            return self.process_response(response_text, fonts)


    # Extrai as principais informações recebidas do webhook da Graph API
    def process_webhook_message(self, data):
        messaging_event = data['entry'][0]['messaging'][0]
        sender_id = messaging_event['sender']['id']
        # Se for o bot que enviou essa mensagem ou se foi o usuário que leu a mensagem enviada pelo bot, para de executar
        if sender_id == '17841474389423643' or "read" in messaging_event:
            return None
        # Se não for uma mensagem, para de executar
        if not ("message" in messaging_event):
            return None
        message = messaging_event["message"]
        text = message["text"] if "text" in message else ""

        self.process_input(sender_id, message, text)

    # Retorna um dicionário com todos os dados necessários das postagens
    def get_content_object(self, sender_id, message, text):

        if "is_unsupported" in message:
            raise VerificaAiException.TypeUnsupported()
        
        content = None
        attachment_message_type = "new_message" if "attachments" in message else None

        if not attachment_message_type:

            try:
                # Se for o link direto de uma postagem
                if text.startswith("https://www.instagram.com/p/") or text.startswith("https://www.instagram.com/reel/"):
                    shortcode = self.get_shortcode_from_url(text)
                    post = instaloader.Post.from_shortcode(self.L.context, shortcode)
                    caption = post.caption if post.caption else ""
                    content = {
                        "is_media": True,
                        "is_link_shared_reel": False,
                        "is_shared_reel": False,
                        "shortcode": shortcode,
                        "post": post,
                        "caption": caption,
                        "data": post.date,
                        "might_execute": True
                    }

                # Se for uma postagem compartilhada em forma de link
                elif text.startswith("https://www.instagram.com/share/"):
                    response = requests.get(text, allow_redirects=True)
                    url = response.url
                    shortcode = self.get_shortcode_from_url(url)
                    post = instaloader.Post.from_shortcode(self.L.context, shortcode)
                    caption = post.caption if post.caption else ""
                    content = {
                        "is_media": True,
                        "is_link_shared_reel": True,
                        "is_shared_reel": False,
                        "shortcode": shortcode,
                        "post": post,
                        "caption": caption,
                        "data": post.date,
                        "might_execute": True
                    }
                
                #se for apenas texto
                else:
                    if sender_id in posts:
                        response_text,_ = self.generate_response([
                            f"Analise a mensagem: \"{text}\"\n. Me retorne apenas 'Sim', se o texto estiver se referindo a algo ou utilizar algum pronome que dá sentido de referência a algo que não está no texto. caso contrário, retorne 'Não'"
                        ])
                        
                        # se a mensagem se refeir a umas postagem previamente enviada
                        if response_text.startswith("Sim"):
                            attachment_message_type = "old_message"
                            posts[sender_id]["might_execute"] = False
                        
                        else:
                            content = { "text": text }

                    else:
                        content = { "text": text }

            except BadResponseException:
                raise VerificaAiException.InvalidLink()

        # Se for postagem compartilhada via aplicativo ou video/imagem enviado pela galeria
        if attachment_message_type == "new_message" or attachment_message_type == "old_message":

            object_if_is_old_message = {
                "sender_id": sender_id,
                "text": text
             } if attachment_message_type == "old_message" else None
            
            message_type = posts[sender_id]["type"] if object_if_is_old_message else message["attachments"][0]["type"]
            
            # Se for uma postagem compartilhada via aplicativo do tipo video
            if message_type == "ig_reel":
                content = { 
                    "type": "video",
                    "shortcode": posts[sender_id]["shortcode"] if object_if_is_old_message else int(message["attachments"][0]["payload"]["reel_video_id"]),
                    "file_src": posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    "caption": posts[sender_id]["caption"] if object_if_is_old_message else message["attachments"][0]["payload"]["title"] if "title" in message["attachments"][0]["payload"] else "",
                    "is_media": True,
                    "is_shared_reel": True,
                    "is_link_shared_reel": False,
                    "object_if_is_old_message": object_if_is_old_message,
                    "might_execute": True
                }

            # Se for um video enviado pela galeria
            elif message_type == "video":
                content = { 
                    "type": "video",
                    "shortcode": posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    "file_src": posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    "caption": "",
                    "is_media": True,
                    "is_shared_reel": False,
                    "is_link_shared_reel": False,
                    "object_if_is_old_message": object_if_is_old_message,
                    "might_execute": True
                }

            # Se for uma postagem do tipo imagem compartilhada via aplicativo ou uma imagem enviada pela galeria
            else:
                content = {
                    "type": "image",
                    "shortcode": posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    "file_src": posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    "caption": "",
                    "is_media": True,
                    "is_shared_reel": True,
                    "is_link_shared_reel": False,
                    "object_if_is_old_message": object_if_is_old_message,
                    "might_execute": True
                }

        if attachment_message_type == "new_message":
            posts[sender_id] = content

        return content
    
    # Eecuta todas as funções necessárias para fazer toda a análise da postagem enviada
    def process_input(self, sender_id, message, text):
        self.send_message_to_user(sender_id, "Estamos analisando o conteúdo. Pode demorar alguns segundos...")
        content = {}
        try:
            content = self.get_content_object(sender_id, message, text)
            response_text = self.get_result_from_process(content)
            if (not ("object_if_is_old_message" in content) or not content["object_if_is_old_message"]) or (content["object_if_is_old_message"] and posts[sender_id]["might_execute"]):
                self.send_message_to_user(sender_id, response_text)

        except VerificaAiException.InvalidLink:
            self.send_message_to_user(sender_id, "Link inválido. Verifique-o e tente novamente.")
            return
        
        except VerificaAiException.TypeUnsupported:
            self.send_message_to_user(sender_id, "Tipo de postagem inválida. Verifique-a e tente novamente.")
            return
        
        except VerificaAiException.GeminiQuotaExceeded:
            self.send_message_to_user(sender_id, "Muitas requisições ao mesmo tempo. Tente novamente mais tarde.")
            return
        
        except VerificaAiException.GraphAPIError as e:
            print(e)

            # Caso a mensagem do usuário supere 2000 caracteres
            if e.args[0]["error"]["message"] == "Length of param message[text] must be less than or equal to 2000":
                self.send_message_to_user(sender_id, "Mensagem muito longa. Envie até 2000 caracteres e tente novamente.")
            
            # Caso a mensagem retornada pelo Gemini seja superior a 1000 caracteres
            else:
                self.send_message_to_user(sender_id, "Ocorreu um erro ao enviar a mensagem. Tente novamente mais tarde.")
            return
        
    def get_final_response(self, response):
        parcial_response, fonts = response.split("Fontes:") if "Fontes:" in response else [response, ""]
        # parcial_response = parcial_response.split("É fato")[1] if "É fato" in parcial_response else parcial_response.split("É fake")[1] if "É fake" in parcial_response else parcial_response


        # x = [self.is_fact_tokenizer.infer_vector(parcial_response.lower().split())]
        x = [parcial_response]

        classe = int(self.is_fact_model.predict(x)[0])
        print(classe)
        if classe == 2:
            return f"✅ É fato\n\n{parcial_response}{fonts}"
        elif classe == 1:
            return f"🤔 Informações insuficientes\n\n{parcial_response}{fonts}"
        else:
            type_fake_class = self.type_fake_name_classes[self.type_fake_model.predict([parcial_response])[0]]
            return f"{type_fake_class}\n\n{parcial_response}{fonts}"


    # Fornece os dados necessários para serem passados para o prompt
    def get_result_from_process(self, content):
        try:
            # Se for imagem ou video
            if "is_media" in content:
                # Retorna o nome do arquivo e o tipo da postagem (imagem/video)
                filename, type = self.process_content(content)
                
                new_content = {
                    "caption": content["caption"],
                    "filename": filename,
                    "object_if_is_old_message": content["object_if_is_old_message"] if "object_if_is_old_message" in content else None,
                    "might_execute": content["might_execute"]
                }
                return self.get_final_response(self.get_response_from_type(type, new_content))

            # Se for texto
            else:
                new_content = { 
                    "text": content["text"]
                }
                return self.get_final_response(self.get_response_from_type("text", new_content))

        except Exception as e:
            print(e)
            traceback.print_exc()