import struct

from flask import Flask, render_template, request, jsonify
import socket
import json
import base64
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TCP_HOST = "192.168.15.3"
TCP_PORT = 63452

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def recv_until_newline(sock):
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Connessione chiusa")
        data += chunk
        if b"\n" in data:
            msg, _ = data.split(b"\n", 1)
            return msg


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat_ai")
def chat_ai():
    return render_template("chat_ai.html")

@app.route("/upload_recipe_book")
def upload_recipe_book():
    return render_template("upload_recipe_book.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "Nessun file inviato"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Nome del file vuoto"}), 400

    if file and file.filename.lower().endswith('.pdf'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        with open(filepath, "rb") as f:
            file_bytes = f.read()

        # 2. Base64
        file_b64 = base64.b64encode(file_bytes).decode("utf-8")

        # 3. JSON payload (ATTENZIONE: chiave deve essere "file", non "pdf")
        payload = {
            "action": "scanpdf",
            "file": file_b64
        }

        payload_bytes = (json.dumps(payload) + "\n").encode("utf-8")

        # 4. Socket TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TCP_HOST, TCP_PORT))

            # invio semplice con newline
            s.sendall(payload_bytes)

            # leggo i primi 4 byte
            header = s.recv(4)
            msg_len = struct.unpack("!I", header)[0]

            # leggo il JSON
            resp_data = s.recv(msg_len)

            response = json.loads(resp_data.decode("utf-8"))
            print(response)

        return jsonify(response), 200
    else:
        return jsonify({"error": "Formato non consentito. Solo PDF."}), 400

@app.route('/chat', methods=['POST'])
def chat():
    payload = {
        "prompt": request.json['prompt'],
        "action": request.json['action'],
    }
    
    payload_bytes = (json.dumps(payload) + "\n").encode("utf-8")

    # 4. Socket TCP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((TCP_HOST, TCP_PORT))

        # invio semplice con newline
        s.sendall(payload_bytes)

        # leggo i primi 4 byte
        header = s.recv(4)
        msg_len = struct.unpack("!I", header)[0]

        # leggo il JSON
        resp_data = s.recv(msg_len)

        response = json.loads(resp_data.decode("utf-8"))
        print(response)

    return jsonify(response), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)