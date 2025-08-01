from enum import Enum

class ShareType(Enum):
    NOT_SHARED = 0          # Postagem original, não compartilhada
    SHARED_VIA_APP = 1      # Compartilhada via aplicativo
    SHARED_VIA_LINK = 2     # Compartilhada via link

class PostType(Enum):
    TEXT = 0,              # Postagem do tipo texto
    IMAGE = 1,             # Postagem do tipo imagem
    VIDEO = 2              # Postagem do tipo video

class AttachmentMessageType(Enum):
    NEW_MESSAGE = 0
    OLD_MESSAGE = 1
    NONE = 2