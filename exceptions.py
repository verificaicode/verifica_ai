from google.genai.errors import ClientError
from instaloader.exceptions import BadResponseException

class VerificaAiException:
    "Tratamento de erros"

    class GeminiQuotaExceeded(ClientError):
        "Limite Gemini API excedido"
        def __init__(self, original: ClientError):
        
            super().__init__(
                original.status,
                original.response.json(),
                getattr(original, 'http_response', None)
            )
    
    class InstaloaderQuotaExceeded(Exception):
        "Limite de requisições com o instaloader atingido"
        pass

    class GraphAPIError(Exception):
        "Erro ocorrido ao tentar enviar a mensagem para o instagram"
        def __init__(self, original: object):
        
            super().__init__(original)

    class InternalError(Exception):
        "Erro interno"
        pass

    class InvalidLink(BadResponseException):
        "Link de post inválido"
        pass

    class TypeUnsupported(Exception):
        "Tipo de post insuportado"
        pass

    class ResponseSearchFormatError(Exception):
        "Resposta da pesquisa realizada pelo Gemini esperava ```json{conteúdo}``` e retornou no formato incorreto. Tenta realizar a pesquisa mais uma vez."
 