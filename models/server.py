from flask import Flask, send_file

app = Flask(__name__)

@app.route("/<path:filename>")
def main(filename):
    return send_file(filename)

app.run("0.0.0.0", 12346)