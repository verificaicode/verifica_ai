import os
from verifica_ai.server import Server
try:
    server = Server()
except KeyboardInterrupt:
    os._exit(0)