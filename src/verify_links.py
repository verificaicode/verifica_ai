import json
import time
from flask import request

class VerifyLinks():
    """
    Classe responsável por lidar com um serviço feito para automatização de verificação de postagens em larga escala, tendo como objetivo avaliar o desempenho desse serviço.
    """

    def __init__(self):
        pass

    def verify_flask(self):
        data = request.get_json()
        if not ("VERIFY_TOKEN" in data) or data["VERIFY_TOKEN"] != self.VERIFY_TOKEN:
            return json.dumps({ "error": "401", "type": "INVALID_TOKEN" }), 200
        
        link = data["link"]
        message = data["message"] if "message" in data else {}

        content = self.process_input("site", str(int(time.time() * 1000)), message, link)
        response_text = self.get_result_from_process(content)

        return json.dumps({ "response": response_text }), 200
    
    async def verify_socketio(self, sid, message):
        data = json.loads(message)
        
        if not ("VERIFY_TOKEN" in data) or data["VERIFY_TOKEN"] != self.VERIFY_TOKEN:
            await self.send_message_to_user_via_site(sid, json.dumps({ "error": "401", "type": "INVALID_TOKEN" })), 200
        
        link = data["link"]
        message = data["message"] if "message" in data else {}

        await self.process_input("site", sid, message, link)