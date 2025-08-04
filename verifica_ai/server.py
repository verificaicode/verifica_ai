import asyncio
import os
from threading import Thread
import time
from flask import Flask, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO as ServerSocketIO
import requests
from socketio import Client as ClientSocketIO
from socketio.exceptions import ConnectionError
from verifica_ai.app_context import AppContext
from verifica_ai.input_handler import InputHandler
from verifica_ai.verify_links import VerifyLinks

class Server(AppContext, InputHandler, VerifyLinks):
    def __init__(self):
        asyncio.run(self.load_app())

    async def load_app(self):
        task = asyncio.create_task(self.run_flask_server())

        AppContext.__init__(self)
        InputHandler.__init__(self)
        VerifyLinks.__init__(self)

        self.app = Flask(__name__)

        CORS(self.app)

        self.io = ClientSocketIO()
        self.socketio = ServerSocketIO(self.app, async_mode='eventlet')

        self.register_routes()

        self.connect_to_server()

        await task
    
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

    def server_socketio_connection(self):
        print("Conectado ao servidor.")

    def server_socketio_message(self, message):
        self.verify_socketio(message)

    def register_routes(self):
        self.io.on("connect", self.connect)
        self.io.on("disconnect", self.disconnect)
        self.io.on("webhook", self.webhook_socketio)

        self.socketio.on_event("connection", self.server_socketio_connection)
        self.socketio.on_event("message", self.server_socketio_message)

        self.app.add_url_rule('/', view_func=self.home, methods=["GET"])
        self.app.add_url_rule('/webhook', view_func=self.webhook_flask, methods=["POST"])
        self.app.add_url_rule('/verify', view_func=self.verify_flask, methods=["POST"])

    def home(self):
        return send_file("public/index.html")

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
            self.socketio.run(self.app, "0.0.0.0", port=5000)
    
    async def run_flask_server(self):
        try:
            flask_thread = Thread(target=self.run_app_flask)
            flask_thread.daemon = True
            flask_thread.start()
            self.loop_task = asyncio.create_task(self.loop())
            await self.loop_task
        except asyncio.CancelledError:
            os._exit(0)