import datetime

from instaloader import Post
from instaloader.exceptions import BadResponseException
import requests

from verifica_ai.exceptions import VerificaAiException
from verifica_ai.schemas.structures import PostContent
from verifica_ai.schemas.types import AttachmentMessageType, PostType, ShareType
from verifica_ai.utils.content_processor import get_http_last_modified, get_shortcode_from_url
from verifica_ai.content_processor.content_extractor import ContentExtractor
from verifica_ai.content_processor.uploader import Uploader
from verifica_ai.content_processor.response_processor import ResponseProcessor

class InputHandler():
    """
    Classe responsável por receber e processar mensagens do webhook da Graph API.

    Controla o fluxo principal do bot: recebe eventos do webhook, filtra mensagens,
    extrai conteúdos, processa a análise e envia resposta para o usuário.
    """

    def process_webhook_message(self, data: dict) -> None:
        """
        Recebe a mensagem bruta da Graph API e inicia seu processamento.

        Filtra mensagens irrelevantes (do próprio bot, leituras, etc), extrai o
        conteúdo relevante e chama `process_input` para continuar o fluxo.

        Parâmetros
        ----------
            data : dict
            Objeto JSON (dicionário) da mensagem enviada pela Graph API.

        Retorna
        -------
            None
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

    def process_input(self, sender_id: int, message: dict, text: str) -> None:
        """
        Processa a mensagem do usuário, gerando análise e enviando resposta.

        Envia uma mensagem inicial de espera para o usuário e executa o
        processamento do conteúdo, tratando erros específicos para informar
        o usuário adequadamente.

        Parâmetros
        ----------
            sender_id : int
                ID do usuário remetente.
            message : dict
                Dados da mensagem recebida.
            text : str
                Texto da mensagem, se disponível.

        Returna
        -------
            None
        """
        extractor = ContentExtractor(self.L, self.posts, self.generate_response)
        uploader = Uploader(self.genai_client)
        response_processor = ResponseProcessor(self.genai_client, self.models, self.content_categories, self.type_fake_name_classes)

        self.send_message_to_user(sender_id, "Estamos analisando o conteúdo. Pode demorar alguns segundos...")

        try:
            post_content = extractor.get_content_object(sender_id, message, text)
            final_response = response_processor.get_result_from_process(post_content)
            if not post_content.object_if_is_old_message or (post_content.object_if_is_old_message and self.posts[sender_id]["might_send_response_to_user"]):
                self.send_message_to_user(sender_id, final_response)

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