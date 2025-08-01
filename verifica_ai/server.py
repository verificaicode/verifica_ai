import asyncio
import os
from threading import Thread
import time

from flask import Flask, request
from flask_cors import CORS
import requests
from socketio import Client
from socketio.exceptions import ConnectionError

from verifica_ai.app_context import AppContext
from verifica_ai.gemini_response_generator import GeminiResponseGenerator
from verifica_ai.input_handler import InputHandler
from verifica_ai.verify_links import VerifyLinks


class Server(AppContext, GeminiResponseGenerator, InputHandler, VerifyLinks):
    def __init__(self):
        AppContext.__init__(self)
        GeminiResponseGenerator.__init__(self)
        InputHandler.__init__(self)
        VerifyLinks.__init__(self)

        self.app = Flask(__name__)

        CORS(self.app)

        self.io = Client()

        self.register_routes()

        self.connect_to_server()

        asyncio.run(self.run_flask_server())

    
    def connect_to_server(self):
        while True:
            try:
                self.io.connect(self.VERIFICA_AI_PROXY)
                time.sleep(1)
            # Erro ao tentar se conectar com o servidor
            except ConnectionError:
                pass

            else:
                break

    def connect(self):
        print("Conectado ao servidor.")

    def disconnect(self):
        print("Desconectado do servidor.")
        self.connect_to_server

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

    def run_app_flask(self):
            self.app.run("0.0.0.0", port=5000)
    
    async def run_flask_server(self):
        try:
            flask_thread = Thread(target=self.run_app_flask)
            flask_thread.daemon = True
            flask_thread.start()
            self.loop_task = asyncio.create_task(self.loop())
            await self.loop_task
        except asyncio.CancelledError:
            os._exit(0)