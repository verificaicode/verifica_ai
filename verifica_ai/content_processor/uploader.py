import os
import time
from google import genai
from google.genai.types import File

class Uploader:
    def __init__(self, client):
        self.client = client

    def upload_file(self, filename: str) -> File:
        file = self.client.files.upload(file=filename)
        state = genai.types.FileState.PROCESSING
        while state == genai.types.FileState.PROCESSING:
            state = self.client.files.get(name=file.name).state
            time.sleep(1)
        os.remove(filename)
        return file
