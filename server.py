from flask import Flask, request
from flask_cors import CORS
import requests
import os
import socketio
from verifai import Verifai
from controls_input import ControlsInput
from verify_links import VerifyLinks
import asyncio
from threading import Thread

class Server(ControlsInput, VerifyLinks):
    def __init__(self):
        Verifai.__init__(self)
        ControlsInput.__init__(self)
        VerifyLinks.__init__(self)

        if os.path.isfile(f"{os.getcwd()}/session/{self.username}"):
            self.L.load_session_from_file(self.username, filename=f"{os.getcwd()}/session/{self.username}")  # se já tiver salvo antes
        else:
            self.L.login(self.username, self.password)  # Vai fazer o login e manter a sessão
            self.L.save_session_to_file(filename=f"{os.getcwd()}/session/{self.username}")

        self.app = Flask(__name__)

        CORS(self.app)

        self.io = socketio.Client()

        self.register_routes()

        if self.DEBUG:
            self.connect_to_server(3)
    
    def connect_to_server(self, attempts):
        try:
            self.io.connect(self.VERIFICA_AI_PROXY)
        
        # Erro ao tentar se conectar com o servidor
        except socketio.exceptions.ConnectionError:
            attempts -= 1
            if attempts > 0:
                self.connect_to_server(attempts)



    def connect(self):
        print("Conectado ao servidor.")

    def disconnect(self):
        print("Desconectado do servidor.")

    def register_routes(self):
        self.io.on("connect", self.connect)
        self.io.on("disconnect", self.disconnect)
        self.io.on("webhook", self.webhook_socketio)

        self.app.add_url_rule('/webhook', view_func=self.webhook_flask, methods=["POST"])
        self.app.add_url_rule('/verify', view_func=self.verify_flask, methods=["POST"])

    def webhook_socketio(self, data):
        self.process_webhook_message(data)

    def webhook_flask(self):
        self.process_webhook_message(request.get_json())

        return "", 200

    async def loop(self):
        while True:
            await asyncio.sleep(10)
            try:
                if not self.DEBUG:
                    requests.get(self.VERIFICA_AI_SERVER)
            except Exception as e:
                print(e)
                pass

    def run_flask(self):
            self.app.run("0.0.0.0", port=5000)
    
    async def main(self):
        try:
            flask_thread = Thread(target=self.run_flask)
            flask_thread.daemon = True
            flask_thread.start()
            self.loop_task = asyncio.create_task(self.loop())
            await self.loop_task
        except asyncio.CancelledError:
            os._exit(0)