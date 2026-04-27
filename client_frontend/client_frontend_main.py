from flask import Flask, render_template, request, jsonify
import socket
import json
import base64
import os

app = Flask(__name__)

TCP_HOST = "127.0.0.1"
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

            # 5. risposta (newline-based)
            resp_data = recv_until_newline(s)
            response = json.loads(resp_data.decode("utf-8"))

        return jsonify({"message": response}), 200
    else:
        return jsonify({"error": "Formato non consentito. Solo PDF."}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



'''
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
        return jsonify({"message": f"File {file.filename} caricato con successo!"}), 200
    else:
        return jsonify({"error": "Formato non consentito. Solo PDF."}), 400

if __name__ == '__main__':
    app.run(port=1717, debug=True)
'''