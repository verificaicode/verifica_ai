import asyncio
import time
import httpx
from quart import Quart, request, send_file
from quart_cors import cors
from socketio import ASGIApp, AsyncServer
from socketio import AsyncClient as AsyncClientSocketIO
from socketio.exceptions import ConnectionError
import uvicorn
from verifica_ai.app_context import AppContext
from verifica_ai.input_handler import InputHandler
from verifica_ai.verify_links import VerifyLinks

class Server(AppContext, InputHandler, VerifyLinks):
    """
    Camada responsável por lidar diretamente com o recebimento de mensagens.
    """

    def __init__(self):
        asyncio.run(self.load_app())


    async def load_app(self):
        task = asyncio.create_task(self.main())

        AppContext.__init__(self)
        InputHandler.__init__(self)
        VerifyLinks.__init__(self)

        app = Quart(__name__)

        cors(app)

        self.io = AsyncClientSocketIO()
        self.socketio = AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',
            ping_interval = 20,
            ping_timeout = 60
        )
        self.app = Quart(__name__)
        self.asgi_app = ASGIApp(self.socketio, self.app)

        self.register_routes()

        if self.DEBUG:
            await self.connect_to_server()

        else:
            await task

    async def connect_to_server(self):
        while True:
            try:
                await self.io.connect(self.VERIFICA_AI_PROXY, auth={
                    "token": self.VERIFY_TOKEN
                })

            # Erro ao tentar se conectar com o servidor
            except ConnectionError:
                await asyncio.sleep(0.5)

            else:
                break

        await self.io.wait()

        await self.connect_to_server()

    def connect(self):
        print("Conectado ao servidor.")

    async def disconnect(self):
        print("Desconectado do servidor.")

    def server_socketio_connection(self):
        print("novo cliente conectado.")

    async def server_socketio_verify(self, sid, message):
        await self.verify_socketio(sid, message)

    def register_routes(self):
        self.io.on("connect", self.connect)
        self.io.on("disconnect", self.disconnect)
        self.io.on("webhook", self.webhook_socketio)

        self.socketio.on("connection", self.server_socketio_connection)
        self.socketio.on("verify", self.server_socketio_verify)

        self.app.add_url_rule('/', view_func=self.home, methods=["GET"])
        self.app.add_url_rule('/webhook', view_func=self.webhook_flask, methods=["POST"])
        self.app.add_url_rule('/verify', view_func=self.verify_flask, methods=["POST"])

    async def home(self):
        return await send_file("public/index.html")

    async def webhook_socketio(self, data):
        await self.process_webhook_message(data)

    async def webhook_flask(self):
        await self.process_webhook_message(await request.get_json())

        return "", 200

    async def keep_alive_loop(self):
        while True:
            await asyncio.sleep(10)
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(self.VERIFICA_AI_SERVER)
            except:
                pass

    # Inicializa tudo no modo assíncrono
    async def main(self):
        # Cria a tarefa do loop de keep-alive
        loop_task = asyncio.create_task(self.keep_alive_loop())

        # Configura e inicia o servidor Uvicorn
        config = uvicorn.Config(app=self.asgi_app, host="0.0.0.0", port=5000)
        server = uvicorn.Server(config)
        await server.serve()