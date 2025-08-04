from dataclasses import dataclass
import datetime
from enum import Enum
from typing import Optional
import instaloader


class ShareType(Enum):
    NOT_SHARED = 0                  # Postagem original, não compartilhada
    SHARED_VIA_APP = 1              # Compartilhada via aplicativo
    SHARED_VIA_LINK = 2             # Compartilhada via link

class PostType(Enum):
    TEXT = 0,                       # Postagem do tipo texto
    IMAGE = 1,                      # Postagem do tipo imagem
    VIDEO = 2                       # Postagem do tipo video
    MEDIA_TYPE_INDETERMINED = 3     # Postagem pode ser video ou imagem

class AttachmentMessageType(Enum):
    NEW_MESSAGE = 0                 # Um novo post será analisado
    OLD_MESSAGE = 1                 # Um antigo post será analisado (por ser referenciado na mensagem atual)
    NONE = 2                        # Não há post a ser analisado

@dataclass
class PostContent:
    """
    Representa os dados processados de uma postagem do Instagram recebida via Graph API.

    A estrutura encapsula informações relevantes como identificação, mídia associada,
    legenda, data da postagem e outras flags que indicam o tipo de conteúdo.

    Atributos
    ---------
    post_type: PostType
        Tipo da postagem.
    
    share_type: ShareType
        Tipo de compartilhamento da postagem.
        
    shortcode : str or None
        Código único da postagem no Instagram.

    post : instaloader.Post or None
        Objeto Instaloader contendo todas as informações sobre o post.

    file_src: str or None
        URL onde está armazenado a mídia da postagem.

    filename: str or None
        caminho da mídia localmente

    caption : str
        Texto da legenda da postagem.

    data : datetime
        Data da publicação da postagem.

    object_if_is_old_message : dict or None
        Se a mensagem atual se referir a algum post anterior, contém um dicionário com os dados desse post.

    might_send_response_to_user : bool
        Flag usada internamente para permitir se a resposta pode ser enviada para o usuário. Se for enviado um post e em seguida uma mensagem que se refere ao post, a resposta ao post será ignorada.
    
    url : str or None
        URL da postagem original.
    
    text : str or None
        Texto da mensagem enviada pelo usuário.
    """
        
    post_type: PostType
    share_type: ShareType
    shortcode: Optional[str]
    post: Optional[instaloader.Post]
    file_src: Optional[str]
    filename: Optional[str]
    caption: str
    data: datetime
    object_if_is_old_message: Optional[dict]
    might_send_response_to_user: bool
    url: Optional[str]
    text: Optional[str]