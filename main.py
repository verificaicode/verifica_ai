import os
from src.server import Server
try:
    server = Server()
except KeyboardInterrupt:
    os._exit(0)