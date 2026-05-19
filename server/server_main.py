import socket
import json
import threading
import base64
import struct
import mysql.connector
from io import BytesIO
from pypdf import PdfReader

HOST = "0.0.0.0"
PORT = 63452

db_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="ricette"
)
cursor = db_conn.cursor()

workers = {}
lock = threading.Lock()

client = None

def findFirstFreeWorker():
    for key, value in workers.items():
        if value["state"] == True:
            return key
        
    return False



def parseMessage(action, payload, conn):
    if action == "hello":
        if payload.get("type") == "worker":
            # with lock:
            workers[conn] = {
                "conn": conn,
                "state": True
            }

            print(len(workers))

            response = {
                "status": "ok",
                "message": "hello ricevuto"
            }

    elif action == "recipes":
        workers[conn]["state"] = True
        
        arr_ricette = payload.get("recipes")

        for recipe in arr_ricette:
            print("Inserimento ricetta")
            cursor.execute("""
                INSERT INTO ricette (nome, porzioni, tempo, tipologia)
                VALUES (%s, %s, %s, %s)
            """, (recipe["nome"], recipe["porzioni"], recipe["tempo_preparazione"], ""))
            recipe_id = cursor.lastrowid

            for ingrediente in recipe["ingredienti"]:
                cursor.execute("""
                    INSERT INTO ingredienti (id_ricetta, nome, quantita)
                    VALUES (%s, %s, %s)
                """, (recipe_id, ingrediente["nome"], ingrediente["quantita"] or ("qb")))
                
            for i, passo in enumerate(recipe["procedimento"]):
                cursor.execute("""
                    INSERT INTO procedimenti (id_ricetta, ordine, descrizione)
                    VALUES (%s, %s, %s)
                """, (recipe_id, i + 1, passo))

            db_conn.commit()

        response = {
            "type": "scanned"
        }

        resp_bytes = (json.dumps(response) + "\n").encode("utf-8")
        client.sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)
        # client.sendall(resp_bytes)

    elif action == "scanpdf":
        client = conn

        file_b64 = payload.get("file")

        if not file_b64:
            response = {
                "status": "error",
                "message": "File mancante"
            }
        else:
            try:
                file_bytes = base64.b64decode(file_b64)

                reader = PdfReader(BytesIO(file_bytes))
                text = ""

                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                response = {
                    "type": "scanpdf",
                    "pdf_text": text
                }

                resp_bytes = (json.dumps(response) + "\n").encode("utf-8")

                conn = findFirstFreeWorker()
                if not conn:
                    print("Tutti i workers occupati")
                    response = {
                        "type": "response",
                        "response": "Ho troppe pentole sul fuoco, attendi un attimo! Riprova tra qualche minuto"
                    }

                    resp_bytes = (json.dumps(response) + "\n").encode("utf-8")
                    client.sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)

                    return

                # first_conn = next(iter(workers))
                workers[conn]["conn"].sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)
                workers[conn]["state"] = False

                print(text)

            except Exception as e:
                print("Errore PDF (forse):", e)
                response = {
                    "status": "error",
                    "message": "Errore parsing PDF"
                }
                
    elif action == "question":
        client = conn
        prompt = payload.get('prompt')
        print(f"Question: {prompt}")
        
        response = {
            "type": "genquery",
            "request": prompt
        }

        resp_bytes = (json.dumps(response) + "\n").encode("utf-8")

        conn = findFirstFreeWorker()
        if not conn:
            print("Tutti i workers occupati")
            response = {
                "type": "response",
                "response": "Ho troppe pentole sul fuoco, attendi un attimo! Riprova tra qualche minuto"
            }

            resp_bytes = (json.dumps(response) + "\n").encode("utf-8")
            client.sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)

            return
        
        workers[conn]["conn"].sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)
        workers[conn]["state"] = False
        
    elif action == "query":
        workers[conn]["state"] = True

        query = payload.get("query")

        print(f"Query: {query}\n\n")

        cursor.execute(query)
        #db_conn.commit()
        
        results = cursor.fetchall()

        print(f"Results: {results}\n\n")
        
        response = {
            "type": "genresponse",
            "request": payload.get("request"),
            "db_response": results
        }

        print(f"Response: {response}\n\n")

        resp_bytes = (json.dumps(response) + "\n").encode("utf-8")

        conn = findFirstFreeWorker()
        if not conn:
            print("Tutti i workers occupati")
            response = {
                "type": "response",
                "response": "Ho troppe pentole sul fuoco, attendi un attimo! Riprova tra qualche minuto"
            }

            resp_bytes = (json.dumps(response) + "\n").encode("utf-8")
            client.sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)

            return
        
        workers[conn]["conn"].sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)
        workers[conn]["state"] = False
        
        
    elif action == "response":
        workers[conn]["state"] = True
        res = payload.get("response")

        print(f"Response: {res}")

        response = {
            "type": "response",
            "response": res
        }

        resp_bytes = (json.dumps(response) + "\n").encode("utf-8")
        client.sendall(struct.pack('!I', len(resp_bytes)) + resp_bytes)
        
    else:
        response = {
            "status": "error",
            "message": "Azione sconosciuta"
        }


def handle_client(conn):
    global client

    with conn:
        print(f"Connessione aperta: {conn}")

        buffer = b""

        try:
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    print("Connessione chiusa dal client")
                    # workers.clear()
                    break

                buffer += chunk

                # processa tutti i messaggi completi (\n)
                while b"\n" in buffer:
                    raw_msg, buffer = buffer.split(b"\n", 1)

                    if not raw_msg:
                        continue

                    try:
                        message = raw_msg.decode("utf-8")

                        payload = json.loads(message)
                        print(payload)

                    except json.JSONDecodeError:
                        conn.sendall(b'{"status":"error","message":"JSON non valido"}\n')
                        continue

                    action = payload.get("action")
                    parseMessage(action=action, payload=payload, conn=conn)

        except Exception as e:
            del workers[conn]
            print(len(workers))
            print("Errore connessione:", e)


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()

        print(f"Server in ascolto su {HOST}:{PORT}...")

        try:
            while True:
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

        except KeyboardInterrupt:
            print("\nServer spento")


start_server()