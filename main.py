from verifiai.server import Server
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

server = Server()

if __name__ == "__main__":
    asyncio.run(server.main())
