from google.genai.errors import ClientError
from instaloader.exceptions import BadResponseException

class VerificaAiException:
    "Tratamento de erros"

    class TypeUnsupported(Exception):
        "Tipo de post insuportado"
        pass

    class InvalidLink(BadResponseException):
        "Link de post inválido"
        pass
    
    class GeminiQuotaExceeded(ClientError):
        "Limite Gemini API excedido"
        def __init__(self, original: ClientError):
        
            super().__init__(
                original.status,
                original.response.json(),
                getattr(original, 'http_response', None)
            )

    class GraphAPIError(Exception):
        "Erro ocorrido ao tentar enviar a mensagem para o instagram."
        def __init__(self, original: object):
        
            super().__init__(original)