from flask import request
import json
import time

class VerifyLinks():
    def __init__(self):
        pass

    def verify_flask(self):
        data = request.get_json()
        if not ("VERIFY_TOKEN" in data) or data["VERIFY_TOKEN"] != self.VERIFY_TOKEN:
            return json.dumps({ "error": "401", "type": "INVALID_TOKEN" }), 200
        
        link = data["link"]
        message = data["message"] if "message" in data else {}

        content = self.get_content_object(str(int(time.time() * 1000)), message, link)
        response_text = self.get_result_from_process(content)

        return json.dumps({ "response": response_text }), 200