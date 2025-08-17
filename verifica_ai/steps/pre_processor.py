import traceback
from datetime import datetime
import httpx
from instaloader import Post
from instaloader.exceptions import BadResponseException
from verifica_ai.exceptions import VerificaAiException
from verifica_ai.handle_gemini_api import HandleGeminiAPI
from verifica_ai.types import AttachmentMessageType, PostContent, PostType, ShareType
from verifica_ai.utils import get_img_index_from_url, get_shortcode_from_url, handle_reel_info

class PreProcessor:
    """
    Classe responsável por gerar um objeto `PostContent` contendo todas as informações necessárias para a análise posterior da mensagem.

    :param instaloader_context: Contém as configurações do instaloader.
    :type instaloader_context: Post

    :param posts: Contém o último post enviado.
    :type posts: dict

    :param TEMP_PATH: Local onde será armazenado temporariamente a imagem ou vídeo da mensagem se houver.
    :type TEMP_PATH:  str

    :param handle_gemini_api: Camada de abstração para a API do Gemini.
    :type handle_gemini_api: HandleGeminiAPI
    """

    def __init__(self, instaloader_context: Post, posts: dict, TEMP_PATH: str, handle_gemini_api: HandleGeminiAPI) -> None:
        self.instaloader_context = instaloader_context
        self.posts = posts
        self.TEMP_PATH = TEMP_PATH
        self.generate_response = handle_gemini_api.generate_response
    
    async def get_result(self, sender_id: int, message: dict, text: str) -> PostContent:
        # Se o tipo da mensgem não for suportado
        if "is_unsupported" in message:
            raise VerificaAiException.TypeUnsupported()

        attachment_message_type = AttachmentMessageType.NEW_MESSAGE if "attachments" in message else AttachmentMessageType.NONE
        sended_timestamp = message["sended_timestamp"]
        post_content = None

        if attachment_message_type == AttachmentMessageType.NONE:
            try:
                # Se o texto da mensagem for o link de uma postagem:
                if text.startswith("https://www.instagram.com/p/") or text.startswith("https://www.instagram.com/reel/"):
                    shortcode = get_shortcode_from_url(text)
                    post = Post.from_shortcode(self.instaloader_context.context, shortcode)
                    caption = post.caption or ""
                    post_content = PostContent(
                        post_type=PostType.MEDIA_TYPE_INDETERMINED,
                        share_type=ShareType.NOT_SHARED,
                        shortcode=shortcode,
                        post=post,
                        file_src=None,
                        filename=None,
                        caption=caption,
                        data=post.date,
                        object_if_is_old_message=None,
                        might_send_response_to_user=True,
                        url=text,
                        text=None,
                        sended_timestamp=sended_timestamp
                    )

                # Se o texto da mensagem for o link de uma postagem compartilhada:
                elif text.startswith("https://www.instagram.com/share/"):
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        response = await client.get(text)

                    url = response.url
                    shortcode = get_shortcode_from_url(url)
                    post = Post.from_shortcode(self.instaloader_context.context, shortcode)
                    caption = post.caption or ""
                    post_content = PostContent(
                        post_type=PostType.MEDIA_TYPE_INDETERMINED,
                        share_type=ShareType.SHARED_VIA_LINK,
                        shortcode=shortcode,
                        post=post,
                        file_src=None,
                        filename=None,
                        caption=caption,
                        data=post.date,
                        object_if_is_old_message=None,
                        might_send_response_to_user=True,
                        url=text,
                        text=None,
                        sended_timestamp=sended_timestamp
                    )

                # Se o texto da mensagem não contiver link:
                else:
                    # Se o usuário tiver enviado algum post anteriormente:
                    if sender_id in self.posts:
                        # Prompt usado para identificar referência de posts na mensagem:
                        response_text, _ = await self.generate_response([
                            f'Analise a mensagem: "{text}". Me retorne apenas "Sim" se a mensagem se refere a algo anterior, caso contrário "Não".'
                        ])

                        # Se o texto da mensagem se referir a algum post enviado anteriormente:
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
                                filename=None,
                                caption="",
                                data=datetime.now(),
                                object_if_is_old_message=None,
                                might_send_response_to_user=True,
                                url=None,
                                text=text,
                                sended_timestamp=sended_timestamp
                            )
                    else:
                        post_content = PostContent(
                            post_type=PostType.TEXT,
                            share_type=ShareType.NOT_SHARED,
                            shortcode=None,
                            post=None,
                            file_src=None,
                            filename=None,
                            caption="",
                            data=datetime.now(),
                            object_if_is_old_message=None,
                            might_send_response_to_user=True,
                            url=None,
                            text=text,
                            sended_timestamp=sended_timestamp
                        )

            except BadResponseException:
                raise VerificaAiException.InvalidLink()

        if attachment_message_type in [AttachmentMessageType.NEW_MESSAGE, AttachmentMessageType.OLD_MESSAGE]:
            object_if_is_old_message = {
                "sender_id": sender_id,
                "text": text
            } if attachment_message_type == AttachmentMessageType.OLD_MESSAGE else None

            message_type = self.posts[sender_id]["type"] if object_if_is_old_message else message["attachments"][0]["type"]
            file_src = self.posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"]

            data, post_type = await handle_reel_info(file_src)

            # Se for um reels compartilhado pelo aplicativo:
            if message_type == "ig_reel":
                post_content = PostContent(
                    post_type=post_type,
                    share_type=ShareType.SHARED_VIA_APP,
                    shortcode=self.posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["reel_video_id"],
                    post=None,
                    file_src=file_src,
                    filename=None,
                    caption=self.posts[sender_id]["caption"] if object_if_is_old_message else message["attachments"][0]["payload"].get("title", ""),
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None,
                    sended_timestamp=sended_timestamp
                )

            # Se for um video enviado da galeria:
            elif message_type == "video":
                post_content = PostContent(
                    post_type=PostType.VIDEO,
                    share_type=ShareType.NOT_SHARED,
                    shortcode=self.posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    post=None,
                    file_src=self.posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    filename=None,
                    caption="",
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None,
                    sended_timestamp=sended_timestamp
                )

            # Se for uma imagem enviada da galeria
            else:
                post_content = PostContent(
                    post_type=PostType.IMAGE,
                    share_type=ShareType.SHARED_VIA_APP,
                    shortcode=self.posts[sender_id]["shortcode"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"].split("=")[1].split("&")[0],
                    post=None,
                    file_src=self.posts[sender_id]["file_src"] if object_if_is_old_message else message["attachments"][0]["payload"]["url"],
                    filename=None,
                    caption="",
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None,
                    sended_timestamp=sended_timestamp
                )

        if attachment_message_type == AttachmentMessageType.NEW_MESSAGE:
            self.posts[sender_id] = post_content

        # Se for video ou imagem:
        if post_content.post_type in [ PostType.IMAGE, PostType.VIDEO, PostType.MEDIA_TYPE_INDETERMINED ]: 
            filename, post_type = await self.handle_post_file(post_content)
            post_content.filename = filename
            post_content.post_type = post_type

        return post_content

    async def handle_post_file(self, post_content: PostContent) -> tuple[str, PostType]:
        """
        Baixa a postagem e extrai seus dados. 
        
        :param post_content: PostContent contendo os dados da postagem

        :return: Uma tupla contendo o caminho do arquivo local e o tipo da postagem
        """
        
        share_type = post_content.share_type
        post_type = post_content.post_type

        try:  
            shortcode = post_content.shortcode
            filename = None

            # Se for uma postagem compartilhada pelo aplicativo do tipo video ou um video enviado pela galeria
            if share_type == ShareType.SHARED_VIA_APP or post_type == PostType.VIDEO:
                async with httpx.AsyncClient() as client:
                    async with client.stream("GET", post_content.file_src) as response:

                        if post_type == PostType.VIDEO:
                            filename = f"{self.TEMP_PATH}/v_{str(shortcode)}_s1.mp4"

                        else:
                            filename = f"{self.TEMP_PATH}/v_{str(shortcode)}_s1.jpg"

                        with open(filename, "wb") as f:
                            async for chunk in response.aiter_bytes(chunk_size=8192):
                                f.write(chunk)

                        return filename, post_type
                
            else:
                post = None
                sufix = "s1"
                url=None

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

                        # post.display_url representa a capa em postagens carrossel
                        # post.video_url representa a URL do video
                        # Se for video armazena sua URL. Se for imagem, pega a capa (a própria imagem)
                        url = url = post.video_url if post.is_video else post.display_url

                    else:
                        raise VerificaAiException.InvalidLink()

                else:
                    post = post_content.post

                    # post.url representa a capa em reels ou post
                    # post.video_url representa a URL do video
                    # Se for video armazena sua URL. Se for imagem, pega a capa (a própria imagem)
                    url = url = post.video_url if post.is_video else post.url

                async with httpx.AsyncClient() as client:
                    async with client.stream("GET", url) as response:

                        # Verifica se a imagem foi baixada com sucesso
                        if response.status_code == 200:
                            if post.is_video:
                                filename = f"{self.TEMP_PATH}/vl_{str(shortcode)}_{sufix}.mp4"
                                post_type = PostType.VIDEO
                            
                            else:
                                filename = f"{self.TEMP_PATH}/vl_{str(shortcode)}_{sufix}.jpg"
                                post_type = PostType.IMAGE

                            with open(filename, "wb") as f:
                                async for chunk in response.aiter_bytes(chunk_size=8192):
                                    f.write(chunk)

                            return filename, post_type
                        
                        else:
                            raise VerificaAiException.InvalidLink()

        # Repassa o erro para o tratamento de erros principal
        except VerificaAiException.InvalidLink():
            raise

        except Exception as e:
            traceback.print_exc()