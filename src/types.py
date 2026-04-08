from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import instaloader

class AttachmentMessageType(Enum):
    """
    Tipo de análise de mensagem com anexo.

    - NEW_MESSAGE: Um novo post será analisado
    - OLD_MESSAGE: Um antigo post será analisado (referência na mensagem atual)
    - NONE: Não há post a ser analisado
    """

    NEW_MESSAGE = 0
    OLD_MESSAGE = 1
    NONE = 2

class PostType(Enum):
    """
    Tipos de conteúdo de um post.

    - TEXT: Postagem do tipo texto
    - IMAGE: Postagem do tipo imagem
    - VIDEO: Postagem do tipo vídeo
    - MEDIA_TYPE_INDETERMINED: Pode ser vídeo ou imagem (não foi possível determinar)
    """

    TEXT = 0
    IMAGE = 1
    VIDEO = 2
    MEDIA_TYPE_INDETERMINED = 3

class ShareType(Enum):
    """
    Tipos de compartilhamento de um post.

    - NOT_SHARED: Postagem original, não compartilhada
    - SHARED_VIA_APP: Compartilhada via aplicativo
    - SHARED_VIA_LINK: Compartilhada via link
    """

    NOT_SHARED = 0
    SHARED_VIA_APP = 1
    SHARED_VIA_LINK = 2

@dataclass
class DetalhedFont:
    """
    Representa uma fonte com mais detalhes.

    :param uri: Uri completa da fonte.
    :type uri: str

    :param domain: Domínio da fonte.
    :type domain: str
    """

    uri: str
    domain: str

@dataclass
class PostContent:
    """
    Representa os dados processados de uma postagem do Instagram recebida via Graph API.

    A estrutura encapsula informações relevantes como identificação, mídia associada,
    legenda, data da postagem e outras flags que indicam o tipo de conteúdo.

    :param post_type: Tipo da postagem.
    :type post_type: PostType
    
    :param share_type: Tipo de compartilhamento da postagem.
    :type share_type: ShareType

    :param shortcode: Código único da postagem no Instagram.
    :type shortcode: str or None

    :param post: Objeto Instaloader contendo todas as informações sobre o post.
    :type post: instaloader.Post or None

    :param file_src: URL onde está armazenado a mídia da postagem.
    :type file_src: str or None

    :param filename: Caminho da mídia localmente.
    :type filename: str or None

    :param caption: Texto da legenda da postagem.
    :type caption: str

    :param data: Data da publicação da postagem.
    :type data: datetime or None

    :param object_if_is_old_message: Se a mensagem atual se referir a algum post anterior, contém um dicionário com os dados desse post.
    :type object_if_is_old_message: dict or None

    :param might_send_response_to_user: Flag usada internamente para permitir se a resposta pode ser enviada para o usuário. Se for enviado um post e em seguida uma mensagem que se refere ao post, a resposta ao post será ignorada.
    :type might_send_response_to_user: bool

    :param url: URL da postagem original.
    :type url: str or None

    :param text: Texto da mensagem enviada pelo usuário.
    :type text: str or None

    :param message_id: Id da mensagem enviada.
    :type message_id: str
    """
        
    post_type: PostType
    share_type: ShareType
    shortcode: Optional[str]
    post: Optional[instaloader.Post]
    file_src: Optional[str]
    filename: Optional[str]
    caption: str
    data: Optional[datetime]
    object_if_is_old_message: Optional[dict]
    might_send_response_to_user: bool
    url: Optional[str]
    text: Optional[str]
    message_id: str