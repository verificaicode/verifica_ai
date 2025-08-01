from instaloader import Post
from instaloader.exceptions import BadResponseException
import requests
from datetime import datetime
from verifica_ai.exceptions import VerificaAiException
from verifica_ai.schemas.structures import PostContent
from verifica_ai.schemas.types import AttachmentMessageType, PostType, ShareType
from verifica_ai.utils.content_processor import get_http_last_modified, get_shortcode_from_url

class ContentExtractor:
    def __init__(self, instaloader_context, posts, generate_response_func):
        self.instaloader_context = instaloader_context
        self.posts = posts
        self.generate_response = generate_response_func

    def get_content_object(self, sender_id: int, message: dict, text: str) -> PostContent:
        if "is_unsupported" in message:
            raise VerificaAiException.TypeUnsupported()

        attachment_message_type = AttachmentMessageType.NEW_MESSAGE if "attachments" in message else AttachmentMessageType.NONE
        post_content = None

        if attachment_message_type == AttachmentMessageType.NONE:
            try:
                if text.startswith("https://www.instagram.com/p/") or text.startswith("https://www.instagram.com/reel/"):
                    shortcode = get_shortcode_from_url(text)
                    post = Post.from_shortcode(self.instaloader_context.context, shortcode)
                    caption = post.caption or ""
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
                elif text.startswith("https://www.instagram.com/share/"):
                    response = requests.get(text, allow_redirects=True)
                    url = response.url
                    shortcode = get_shortcode_from_url(url)
                    post = Post.from_shortcode(self.instaloader_context.context, shortcode)
                    caption = post.caption or ""
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
                else:
                    # Texto comum ou referindo postagem antiga
                    if sender_id in self.posts:
                        response_text, _ = self.generate_response([
                            f'Analise a mensagem: "{text}". Me retorne apenas "Sim" se a mensagem se refere a algo anterior, caso contrário "Não".'
                        ])
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
                                caption="",
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
                            caption="",
                            data=datetime.now(),
                            object_if_is_old_message=None,
                            might_send_response_to_user=True,
                            url=None,
                            text=text
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
            data = get_http_last_modified(file_src)

            if message_type == "ig_reel":
                post_content = PostContent(
                    post_type=PostType.VIDEO,
                    share_type=ShareType.SHARED_VIA_APP,
                    shortcode=self.posts[sender_id]["shortcode"] if object_if_is_old_message else int(message["attachments"][0]["payload"]["reel_video_id"]),
                    post=None,
                    file_src=file_src,
                    caption=self.posts[sender_id]["caption"] if object_if_is_old_message else message["attachments"][0]["payload"].get("title", ""),
                    data=data,
                    object_if_is_old_message=object_if_is_old_message,
                    might_send_response_to_user=True,
                    url=None,
                    text=None
                )
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
