import requests
import os
import instaloader
from instaloader import BadResponseException
import time
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, File
from google.genai.errors import ClientError
from verifica_ai.exceptions import VerificaAiException
from verifica_ai.utils import get_shortcode_from_url, get_img_index_from_url, get_final_urls, get_http_last_modified
from verifica_ai.types import PostContent, PostType, ShareType, AttachmentMessageType
from datetime import datetime

load_dotenv()

posts = {}

class ControlsInput():
    def __init__(self):
        with open(f"prompts/content_categories.txt", 'r', encoding='utf-8') as f:
            self.content_categories = f.read() 

    # Envia o arquivo do post (imagem/video) para o servidor da GEMINI API
    def upload_file(self, filename: str) -> File:
        """
        Envia o arquivo para o servidor do Gemini e apaga localmente

        Parâmetros
        ----------
        filename: str
            Arquivo a ser manipulado

        Retorna
        -------
        file : File
            Objeto File representando o arquivo enviado pela API.
        """

        file = self.client.files.upload(file = filename)

        state = genai.types.FileState.PROCESSING
        while state == genai.types.FileState.PROCESSING:
            state = self.client.files.get(name = file.name).state
            time.sleep(1)
        
        os.remove(filename)

        return file

    # Extrai o texto (e as fontes caso necessário) do objeto de resposta retornado da GEMINI API
    def get_text_from_prompt(self, response):
        if len(response.candidates) > 0 and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            fonts = []
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                fonts.append(chunk.web.uri)
            text = ""
            for part in response.candidates[0].content.parts:
                text += part.text

            return [ text, get_final_urls(fonts) ]
        
        return response.text

    def process_response(self, response_text: str, fonts: list[str]) -> str:
        """
        Processa a resposta gerada pelo Gemini.

        Garante que a resopsta final não ultrapasse 960 caracteres, colocando o máximo de fontes possível que não ultrapasse o limite.
        
        Parâmetros
        ----------
        response_text : str
            Resposta bruta retornada pelo Gemini.

        fonts: list of str
            Uma lista contendo as fontes utilizadas para as pesquisas acerca do conteúdo da mensagem.

        Retorna
        -------
        response_text : str
            String contendo a explicação e suas fontes.
        """

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
    def process_content(self, post_content: PostContent):
        share_type = post_content.share_type
        post_type = post_content.post_type

        try:  
            shortcode = post_content.shortcode
            filename = None

            # Se for uma postagem compartilhada pelo aplicativo do tipo video ou um video enviado pela galeria
            if share_type == ShareType.SHARED_VIA_APP or post_type == PostType.VIDEO:
                response = requests.get(post_content.file_src, stream=True)

                if post_type == PostType.VIDEO:
                    filename = f"{self.temp_path}/v_{str(shortcode)}_s1.mp4"

                else:
                    filename = f"{self.temp_path}/v_{str(shortcode)}_s1.jpg"

                with open(filename, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                return filename
                
            else:
                self.L.download_post(post_content.post, target="tmp/files")

                post = None
                sufix = "_s1"

                # Se for uma postagem com multiplas mídias
                multimidia = post_content.post.typename == 'GraphSidecar'

                if multimidia:

                    # Obtém todos os posts da postagem
                    posts = list(post_content.post.get_sidecar_nodes())

                    # Pega o indice da mídia no qual o usuário compartilhou o link
                    img_index = get_img_index_from_url(post_content.url) - 1
                    
                    # Se existir uma postagem para o indice obtido
                    if img_index < len(posts):
                        # Mídia do link
                        post = posts[img_index]
                        sufix = f"_m{img_index}"

                    else:
                        raise VerificaAiException.InvalidLink()

                else:
                    post = post_content.post

                url = post.display_url

                response = requests.get(url)

                # Verifica se a imagem foi baixada com sucesso
                if response.status_code == 200:
                    if post_type == PostType.VIDEO:
                        filename = f"{self.temp_path}/vl_{str(shortcode)}_{sufix}.mp4"
                    
                    else:
                        filename = f"{self.temp_path}/vl_{str(shortcode)}_{sufix}.jpg"

                    with open(filename, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    return filename

                else:
                    raise VerificaAiException.InvalidLink()

        except Exception as e:
            traceback.print_exc()

        # Repassa o erro para o tratamento de erros principal
        except VerificaAiException.InvalidLink():
            raise VerificaAiException.InvalidLink()

    def send_message_to_user(self, user_id, message_text):
        """
            Envia mensagem para o usuário

            Parâmetros
            ----------
            user_id : number
                Td do usuário para enviar a mensagem

            message_text : str
                Texto a ser enviado
        """

        url = "https://graph.instagram.com/v22.0/me/messages"
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
    def get_response_from_type(self, post_content: PostContent) -> str:
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

    def process_webhook_message(self, data: dict) -> None:
        """
        Processa a mensagem recebida da Graph API.

        Esta função extrai e manipula os dados recebidos diretamente do webhook da Graph API, tratando eventos e preparando-os para processamento posterior.

        Parâmetros
        ----------
        data : dict
            Objeto JSON (dicionário) contendo os dados brutos enviados pela Graph API.

        Retorna
        -------
        None
            Esta função não retorna nenhum valor.
        """

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
    def get_content_object(self, sender_id: int, message: dict, text: str) -> PostContent:
        # Caso o tipo de postagem seja inválida
        if "is_unsupported" in message:
            raise VerificaAiException.TypeUnsupported()
        
        post_content = None
        attachment_message_type = AttachmentMessageType.NEW_MESSAGE if "attachments" in message else AttachmentMessageType.NONE

        #Se a mensagem for um texto
        if attachment_message_type == AttachmentMessageType.NONE:

            try:
                # Se for o link direto de uma postagem
                if text.startswith("https://www.instagram.com/p/") or text.startswith("https://www.instagram.com/reel/"):
                    shortcode = get_shortcode_from_url(text)
                    post = instaloader.Post.from_shortcode(self.L.context, shortcode)
                    caption = post.caption if post.caption else ""
                    post_content = PostContent(
                        post_type=PostType.VIDEO if post.is_video else PostType.IMAGE,
                        share_type=ShareType.NOT_SHARED,
                        shortcode=shortcode,
                        post=post,
                        file_src=None,
                        caption=caption,
                        data=post.date,
                        object_if_is_old_message=None,
                        might_send_response_to_user=True,
                        url=text,
                        text=None
                    )

                # Se for uma postagem compartilhada em forma de link
                elif text.startswith("https://www.instagram.com/share/"):
                    response = requests.get(text, allow_redirects=True)
                    url = response.url
                    shortcode = self.get_shortcode_from_url(url)
                    post = instaloader.Post.from_shortcode(self.L.context, shortcode)
                    caption = post.caption if post.caption else ""
                    post_content = PostContent(
                        post_type=PostType.VIDEO if post.is_video else PostType.IMAGE,
                        share_type=ShareType.SHARED_VIA_LINK,
                        shortcode=shortcode,
                        post=post,
                        file_src=None,
                        caption=caption,
                        data=post.date,
                        object_if_is_old_message=None,
                        might_send_response_to_user=True,
                        url=text,
                        text=None
                    )
                
                # Se for apenas texto
                else:
                    if sender_id in posts:
                        response_text,_ = self.generate_response([
                            f"Analise a mensagem: \"{text}\"\n. Me retorne apenas 'Sim', se o texto estiver se referindo a algo ou utilizar algum pronome que dá sentido de referência a algo que não está no texto. caso contrário, retorne 'Não'"
                        ])
                        
                        # Se a mensagem se refeir a umas postagem previamente enviada
                        if response_text.startswith("Sim"):
                            attachment_message_type = AttachmentMessageType.OLD_MESSAGE
                            posts[sender_id]["might_send_response_to_user"] = False
                        
                        else:
                            post_content = PostContent(
                                post_type=PostType.TEXT,
                                share_type=ShareType.NOT_SHARED,
                                shortcode=None,
                                post=None,
                                file_src=None,
                                caption=caption,
                                data=datetime.now(),
                                object_if_is_old_message=None,
                                might_send_response_to_user=True,
                                url=None,
                                text=text
                            )

                    else:
                        post_content = PostContent(
                            post_type=PostType.TEXT,
                            share_type=ShareType.NOT_SHARED,
                            shortcode=None,
                            post=None,
                            file_src=None,
                            caption=caption,
                            data=datetime.now(),
                            object_if_is_old_message=None,
                            might_send_response_to_user=True,
                            url=None,
                            text=text
                        )


            except BadResponseException:
                raise VerificaAiException.InvalidLink()

        # Se a mensagem for uma postagem nova ou um texto que se refere a uma postagem
        if attachment_message_type == AttachmentMessageType.NEW_MESSAGE or attachment_message_type == AttachmentMessageType.OLD_MESSAGE:

            object_if_is_old_message = {
                "sender_id": sender_id,
                "text": text
             } if attachment_message_type == AttachmentMessageType.OLD_MESSAGE else None
            
            message_type = posts[sender_id]["type"] if object_if_is_old_message else message["attachments"][0]["type"]
            
            file_src = posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"]

            data = get_http_last_modified(file_src)
            
            # Se for uma postagem compartilhada via aplicativo do tipo video
            if message_type == "ig_reel":
                post_content = PostContent(
                    post_type=PostType.VIDEO,
                    share_type=ShareType.SHARED_VIA_APP,
                    shortcode=posts[sender_id]["shortcode"] if object_if_is_old_message else int(message["attachments"][0]["payload"]["reel_video_id"]),
                    post=None,
                    file_src=file_src,
                    caption=posts[sender_id]["caption"] if object_if_is_old_message else message["attachments"][0]["payload"]["title"] if "title" in message["attachments"][0]["payload"] else "",
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None
                )

            # Se for um video enviado pela galeria
            elif message_type == "video":
                post_content = PostContent(
                    post_type=PostType.VIDEO,
                    share_type=ShareType.NOT_SHARED,
                    shortcode=posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    post=None,
                    file_src=posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    caption="",
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None
                )

            # Se for uma postagem do tipo imagem compartilhada via aplicativo ou uma imagem enviada pela galeria
            else:
                post_content = PostContent(
                    post_type=PostType.IMAGE,
                    share_type=ShareType.SHARED_VIA_APP,
                    shortcode=posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    post=None,
                    file_src=posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    caption="",
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None
                )

        if attachment_message_type == AttachmentMessageType.NEW_MESSAGE:
            posts[sender_id] = post_content

        return post_content
    
    def process_input(self, sender_id: int, message: dict, text: str) -> None:
        """
        Processa a mensagem do usuário.

        Executa as principais funções que realizam todo o processamento do chatbot.
        
        Parâmetros
        ----------
        sender_id : int
            Id do usuário que está enviando a mensagem.

        message : dict
            Dicionário contendo todos os dados da postagem enviada.

        text : str
            Texto caso a mensagem recebida for do tipo texto

        Retorna
        -------
        None
            Esta função não retorna nenhum valor.
        """

        self.send_message_to_user(sender_id, "Estamos analisando o conteúdo. Pode demorar alguns segundos...")

        try:
            post_content = self.get_content_object(sender_id, message, text)
            response_text = self.get_result_from_process(post_content)
            if not post_content.object_if_is_old_message or (post_content.object_if_is_old_message and posts[sender_id]["might_send_response_to_user"]):
                self.send_message_to_user(sender_id, response_text)

        # Tratamento de erros
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

    # Fornece os dados necessários para serem passados para o prompt
    def get_result_from_process(self, post_content):
        try:
            # Se for imagem ou video
            if post_content.post_type == PostType.IMAGE or post_content.post_type == PostType.VIDEO:
                # Retorna o nome do arquivo
                post_content.filename = self.process_content(post_content)

                return self.get_response_from_type(post_content)

            # Se for texto
            else:
                return self.get_response_from_type(post_content)

        except Exception as e:
            print(e)
            traceback.print_exc()