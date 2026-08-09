from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import random
import sys

from app.characters.characters_identity import CharacterIdentity, generate_identity
from app.characters.characters_races import get_available_races
from app.characters.characters_languages import get_available_languages, get_race_languages
from app.database.characters_db import (
    init_database,
    save_identity,
    update_identity,
    get_identity,
    get_all_identities,
    delete_character,
)

HOST = "127.0.0.1"
PORT = 8000
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"


def json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def identity_to_dict(identity, character_id=None):
    result = {
        "name": identity.name,
        "surname": identity.surname,
        "nickname": identity.nickname,
        "age": identity.age,
        "birth_date": identity.birth_date,
        "sex": identity.sex,
        "race": identity.race,
        "physical_description": identity.physical_description,
        "appearance": identity.appearance,
    }
    if character_id is not None:
        result["id"] = character_id
    return result


def identity_from_dict(data):
    if not isinstance(data, dict):
        raise ValueError("I dati del personaggio devono essere un oggetto JSON.")

    identity = CharacterIdentity(
        name=str(data.get("name", "")).strip(),
        surname=str(data.get("surname", "")).strip(),
        nickname=str(data.get("nickname", "")).strip(),
        age=int(data.get("age", 0)),
        birth_date=str(data.get("birth_date", "")).strip(),
        sex=str(data.get("sex", "")).strip(),
        race=str(data.get("race", "")).strip(),
        physical_description=str(data.get("physical_description", "")).strip(),
        appearance=str(data.get("appearance", "")).strip(),
    )

    from app.characters.characters_identity import validate_identity
    validate_identity(identity_to_dict(identity))
    return identity


def generate_character():
    races = get_available_races()
    if not races:
        raise ValueError("Non sono presenti razze disponibili.")

    weights = [max(0.0, float(race.rarity)) for race in races]
    if not any(weights):
        weights = None

    race = random.choices(races, weights=weights, k=1)[0]
    identity = generate_identity(race.name)
    languages = get_race_languages(race.name)

    return {
        "identity": identity_to_dict(identity),
        "languages": [
            {
                "language_id": language.language_id,
                "name": language.name,
                "comprehension": language.comprehension,
                "speaking": language.speaking,
                "writing": language.writing,
            }
            for language in languages
        ]
    }


class RPGServer(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[SERVER] {self.address_string()} - {format % args}")

    def do_GET(self):
        try:
            request_path = self.path.split("?", 1)[0].rstrip("/") or "/"

            if request_path == "/api/races":
                json_response(self, [
                    {
                        "id": race.id,
                        "name": race.name,
                        "description": race.description,
                        "average_height": race.average_height,
                        "average_weight": race.average_weight,
                        "lifespan": race.lifespan,
                        "rarity": race.rarity,
                    }
                    for race in get_available_races()
                ])
                return

            if request_path == "/api/languages":
                json_response(self, [
                    {
                        "id": language.id,
                        "name": language.name,
                        "prevalence": language.prevalence,
                        "difficulty": language.difficulty,
                    }
                    for language in get_available_languages()
                ])
                return

            if request_path == "/api/characters":
                json_response(self, get_all_identities())
                return

            if request_path.startswith("/api/characters/"):
                character_id = int(request_path.rsplit("/", 1)[1])
                identity = get_identity(character_id)
                if identity is None:
                    json_response(self, {"error": "Personaggio non trovato."}, 404)
                    return

                languages = get_race_languages(identity.race)
                json_response(self, {
                    "id": character_id,
                    "identity": identity_to_dict(identity, character_id),
                    "languages": [
                        {
                            "language_id": language.language_id,
                            "name": language.name,
                            "comprehension": language.comprehension,
                            "speaking": language.speaking,
                            "writing": language.writing,
                        }
                        for language in languages
                    ]
                })
                return

            self.serve_frontend()

        except ValueError:
            json_response(self, {"error": "ID personaggio non valido."}, 400)
        except Exception as error:
            print("[SERVER ERROR]", error)
            json_response(self, {"error": str(error)}, 500)

    def do_POST(self):
        try:
            request_path = self.path.split("?", 1)[0].rstrip("/")

            if request_path == "/api/generate-character":
                json_response(self, generate_character())
                return

            if request_path == "/api/characters":
                data = self.read_json()
                identity_data = data.get("identity", data)
                character_id = data.get("id")
                identity = identity_from_dict(identity_data)

                if character_id is None or str(character_id).strip() == "":
                    character_id = save_identity(identity)
                    print(f"[DATABASE] Personaggio creato: ID {character_id}")
                else:
                    character_id = int(character_id)
                    update_identity(character_id, identity)
                    print(f"[DATABASE] Personaggio aggiornato: ID {character_id}")

                json_response(self, {
                    "success": True,
                    "id": character_id,
                    "identity": identity_to_dict(identity, character_id),
                })
                return

            if request_path == "/api/race-languages":
                data = self.read_json()
                race = data.get("race")
                if not isinstance(race, str) or not race.strip():
                    json_response(self, {"error": "Razza non specificata."}, 400)
                    return

                json_response(self, [
                    {
                        "language_id": language.language_id,
                        "name": language.name,
                        "comprehension": language.comprehension,
                        "speaking": language.speaking,
                        "writing": language.writing,
                    }
                    for language in get_race_languages(race)
                ])
                return

            json_response(self, {"error": "Endpoint non trovato."}, 404)

        except ValueError as error:
            json_response(self, {"error": str(error)}, 400)
        except Exception as error:
            print("[SERVER ERROR]", error)
            json_response(self, {"error": str(error)}, 500)

    def do_DELETE(self):
        try:
            request_path = self.path.split("?", 1)[0].rstrip("/")

            if request_path.startswith("/api/characters/"):
                character_id = int(request_path.rsplit("/", 1)[1])
                delete_character(character_id)
                print(f"[DATABASE] Personaggio eliminato: ID {character_id}")
                json_response(self, {"success": True, "id": character_id})
                return

            json_response(self, {"error": "Endpoint non trovato."}, 404)
        except ValueError as error:
            json_response(self, {"error": str(error)}, 400)
        except Exception as error:
            print("[SERVER ERROR]", error)
            json_response(self, {"error": str(error)}, 500)

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        raw_data = self.rfile.read(content_length)
        return json.loads(raw_data.decode("utf-8"))

    def serve_frontend(self):
        request_path = self.path.split("?", 1)[0]
        if request_path == "/":
            request_path = "/index.html"

        file_path = (FRONTEND_DIR / request_path.lstrip("/")).resolve()

        try:
            file_path.relative_to(FRONTEND_DIR.resolve())
        except ValueError:
            self.send_error(403, "Accesso negato.")
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File non trovato.")
            return

        mime_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        content_type = mime_types.get(file_path.suffix.lower(), "application/octet-stream")

        try:
            data = file_path.read_bytes()
        except OSError as error:
            self.send_error(500, str(error))
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    if not FRONTEND_DIR.exists():
        print(f"Frontend non trovato: {FRONTEND_DIR}")
        sys.exit(1)

    init_database()

    server = HTTPServer((HOST, PORT), RPGServer)

    print()
    print("=" * 60)
    print("AI RPG SERVER")
    print("=" * 60)
    print()
    print(f"Server: http://{HOST}:{PORT}")
    print(f"Frontend: {FRONTEND_DIR}")
    print("Database: data/characters.db")
    print()
    print("Premi CTRL+C per fermare il server.")
    print()
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Arresto server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
