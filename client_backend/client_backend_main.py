import json
import socket
import logging
from langchain_community.llms import Ollama

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 63452

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
ollama = Ollama(model = "qwen3.5:4b")

def split_recipes(full_text):
    logger.info("Extracting recipes from text")
    response = ollama.invoke([
    {
        "role": "system",
        "content": "Sei un assistente specializzato nell'estrazione strutturata di ricette da testi.\n            Estrai TUTTE le ricette presenti nel testo fornito.\n            Rispondi SOLO con un array JSON valido, senza markdown, senza testo aggiuntivo.\n            \n            Ogni ricetta deve avere questo schema:\n            {\n                \"nome\": \"string\",\n                \"porzioni\": \"string | null\",\n                \"tempo_preparazione\": \"string | null\",\n                \"tempo_cottura\": \"string | null\",\n                \"difficolta\": \"string | null\",\n                \"ingredienti\": [\n                    { \"quantita\": \"string | null\", \"unita\": \"string | null\", \"nome\": \"string\" }\n                ],\n                \"procedimento\": [\"step1\", \"step2\", ...],\n                \"note\": \"string | null\"\n            }\n            \n            REGOLE IMPORTANTI:\n            - Se una ricetta sembra incompleta (testo troncato a inizio o fine), non estrarla.\n            - Se non trovi ricette, restituisci un array vuoto: []\n            - Non inventare dati mancanti, usa null.\n            - Normalizza le unità di misura (g, kg, ml, l, cucchiai, cucchiaini, tazze...).\n"
    },
    {
        "role": "user",
        "content": full_text
    }])
    
    logger.debug(f"Ollama response for recipe extraction: {response}")
    return json.loads(response)

def generate_query(user_request):
    logger.info(f"Generating query for user request: {user_request}")
    response = ollama.invoke([
    {
        "role": "system",
        "content": f"""Sei un assistente che trasforma richieste in query strutturate.
            Riceverai una richiesta testuale e dovrai rispondere SOLO con una query SQL valida, senza markdown, senza testo aggiuntivo.
            
            Lo schema del database è il seguente:
            - ricette(id, nome, porzioni, tempo, tipologia)
            - ingredienti(id, id_ricetta, nome, quantita)  
            - procedimenti(id, id_ricetta, ordine, descrizione)

            Devi analizzare la richiesta e generare una query SQL che estragga le informazioni richieste.
            """
    },
    {
        "role": "user",
        "content": user_request
    }])
    print(response)
    return json.loads(response)

def generate_response(user_request, db_response):
    logger.info(f"Generating response for user request: {user_request} with db response: {db_response}")
    response = ollama.invoke([
    {
        "role": "system",
        "content": f"""Sei un assistente che trasforma risposte di database in risposte testuali per l'utente.
            Riceverai una richiesta testuale e una risposta del database (in formato JSON).
            Devi rispondere SOLO con una risposta testuale chiara e concisa, senza markdown, senza testo aggiuntivo.
            
            La risposta del database sarà un array di oggetti, ad esempio:
            [
                {"nome": "Pasta al pomodoro", "porzioni": 4, "tempo": "30 min", "tipologia": "primo"},
                ...
            ]

            Analizza la richiesta e la risposta del database e genera una risposta testuale che soddisfi la richiesta dell'utente.
            """
    },
    {
        "role": "user",
        "content": f"Richiesta: {user_request}\nRisposta DB: {json.dumps(db_response)}"
    }])
    logger.debug(f"Ollama response for text transformation: {response}")
    return response

def handle_message(message):
    if message["type"] == "scanpdf":
        full_text = message["pdf_text"]
        # recipes = split_recipes(full_text)
        # load from file
        with open("fake_rec.json", "r") as f:
            recipes = json.load(f)
        return {"action": "recipes", "recipes": recipes}
    elif message["type"] == "genquery":
        user_request = message["request"]
        query = generate_query(user_request)
        return {"action": "query", "query": query}
    elif message["type"] == "genresponse":
        user_request = message["request"]
        db_response = message["db_response"]
        response = generate_response(user_request, db_response)
        return {"action": "response", "response": response}
    else:
        logger.warning(f"Unknown message type: {message['type']}")
        return {"error": "Unknown message type"}

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_HOST, SERVER_PORT))
        logger.info("Connected to server")
        s.sendall((json.dumps({"type": "worker", "action": "hello", "name": "worker1"}) + "\n").encode())

        while True:
            data = s.recv(24*1024)  # Receive up to 24KB of data
            string = data.decode().strip()

            # remove characters before the first '{' and after the last '}' to ensure we have a valid JSON string
            string = string[string.find('{'):string.rfind('}')+1]

            logger.debug(f"Received data: {string}")
            if not data:
                break
            message = json.loads(string)

            response = handle_message(message)
            s.sendall((json.dumps(response) + "\n").encode())
            logger.info("Sent response back to server")

if __name__ == "__main__":
    main()