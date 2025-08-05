import requests
import traceback
from flask_socketio import emit
from verifica_ai.exceptions import VerificaAiException
from verifica_ai.steps.pre_processor import PreProcessor
from verifica_ai.steps.processor import Processor
from verifica_ai.steps.pos_processor import PosProcessor

class InputHandler():
    """
    Classe responsável por receber e processar mensagens do webhook da Graph API.

    Controla o fluxo principal do bot: recebe eventos do webhook, filtra mensagens,
    extrai conteúdos, processa a análise e envia resposta para o usuário.
    """

    async def process_webhook_message(self, data: dict) -> None:
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

        await self.process_input("instagram", sender_id, message, text)

    async def process_input(self, user_received: str, sender_id: int, message: dict, text: str) -> None:
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

        self.response_user(user_received, sender_id, "Estamos analisando o conteúdo. Pode demorar alguns segundos...")

        try:
            pre_processor_result = await PreProcessor(self.instaloader_context, self.posts, self.TEMP_PATH).get_result(sender_id, message, text)
            processor_result = await Processor(self.genai_client, self.model, self.google_search_tool).get_result(pre_processor_result)
            pos_processor_result = PosProcessor().get_result(processor_result)

            if not pre_processor_result.object_if_is_old_message or (pre_processor_result.object_if_is_old_message and self.posts[sender_id]["might_send_response_to_user"]):
                self.response_user(user_received, sender_id, pos_processor_result)

        # Tratamento de erros
        except VerificaAiException.InternalError:
            self.response_user(user_received, sender_id, "Ocorreu um erro ao processar a mensagem. Tente novamente mais tarde.")

        except VerificaAiException.InvalidLink:
            self.response_user(user_received, sender_id, "Link inválido. Verifique-o e tente novamente.")
            return
        
        except VerificaAiException.TypeUnsupported:
            self.response_user(user_received, sender_id, "Tipo de postagem inválida. Verifique-a e tente novamente.")
            return
        
        except VerificaAiException.GeminiQuotaExceeded:
            traceback.print_exc()
            self.response_user(user_received, sender_id, "Muitas requisições ao mesmo tempo. Tente novamente mais tarde.")
            return
        
        except VerificaAiException.GraphAPIError as e:
            traceback.print_exc()

            # Caso a mensagem do usuário supere 2000 caracteres
            if e.args[0]["error"]["message"] == "Length of param message[text] must be less than or equal to 2000":
                self.response_user(user_received, sender_id, "Mensagem muito longa. Envie até 2000 caracteres e tente novamente.")
            
            # Caso a mensagem retornada pelo Gemini seja superior a 1000 caracteres
            else:
                self.response_user(user_received, sender_id, "Ocorreu um erro ao enviar a mensagem. Tente novamente mais tarde.")
            return
        
    def response_user(self, user_received, sender_id, message_text):
        if user_received == "instagram":
            self.send_message_to_user_via_instagram(sender_id, message_text)

        else:
            self.send_message_to_user_via_site(sender_id, message_text)

    def send_message_to_user_via_site(self, sender_id, message_text):
        self.socketio.emit("message", message_text, boradcast=True)

    def send_message_to_user_via_instagram(self, sender_id: int, message_text: str):
        """
            Envia mensagem para o usuário

            :param sender_id: Id do usuário para enviar a mensagem

            :param message_text: Texto a ser enviado
        """

        url = "https://graph.instagram.com/v22.0/me/messages"
        payload = {
            "messaging_product": "instagram",
            "recipient": {"id": sender_id},
            "message": {"text": message_text}
        }
        headers = {
            "Authorization": f"Bearer {self.PAGE_ACCESS_TOKEN}"
        }
        v = requests.post(url, headers=headers, json=payload).json()

        # Verifica se ocorreu um erro ao tentar enviar a mensagem.
        if "error" in v:
            raise VerificaAiException.GraphAPIError(v)
