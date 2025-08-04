from datetime import datetime
import os
import traceback
import time

from google import genai
from google.genai.types import File
from instaloader import Post
from instaloader.exceptions import BadResponseException
import requests

from verifica_ai.exceptions import VerificaAiException
from verifica_ai.schemas.structures import PostContent
from verifica_ai.verifica_ai.types import AttachmentMessageType, PostType, ShareType
from verifica_ai.verifica_ai.utils import get_final_urls, get_http_last_modified, get_shortcode_from_url


class ContentProcessor():
    """
        Classe responsável por processar a mensagem recebida do webhook
    """

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
                    post = Post.from_shortcode(self.L.context, shortcode)
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
                    post = Post.from_shortcode(self.L.context, shortcode)
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
                    if sender_id in self.posts:
                        response_text,_ = self.generate_response([
                            f"Analise a mensagem: \"{text}\"\n. Me retorne apenas 'Sim', se o texto estiver se referindo a algo ou utilizar algum pronome que dá sentido de referência a algo que não está no texto. caso contrário, retorne 'Não'"
                        ])
                        
                        # Se a mensagem se refeir a umas postagem previamente enviada
                        if response_text.startswith("Sim"):
                            attachment_message_type = AttachmentMessageType.OLD_MESSAGE
                            self.posts[sender_id]["might_send_response_to_user"] = False
                        
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
            
            message_type = self.posts[sender_id]["type"] if object_if_is_old_message else message["attachments"][0]["type"]
            
            file_src = self.posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"]

            data = get_http_last_modified(file_src)
            
            # Se for uma postagem compartilhada via aplicativo do tipo video
            if message_type == "ig_reel":
                post_content = PostContent(
                    post_type=PostType.VIDEO,
                    share_type=ShareType.SHARED_VIA_APP,
                    shortcode=self.posts[sender_id]["shortcode"] if object_if_is_old_message else int(message["attachments"][0]["payload"]["reel_video_id"]),
                    post=None,
                    file_src=file_src,
                    caption=self.posts[sender_id]["caption"] if object_if_is_old_message else message["attachments"][0]["payload"]["title"] if "title" in message["attachments"][0]["payload"] else "",
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
                    shortcode=self.posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    post=None,
                    file_src=self.posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
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
                    shortcode=self.posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    post=None,
                    file_src=self.posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    caption="",
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None
                )

        if attachment_message_type == AttachmentMessageType.NEW_MESSAGE:
            self.posts[sender_id] = post_content

        return post_content
    
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

    # Fornece os dados necessários para serem passados para o prompt
    def get_result_from_process(self, post_content):
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
