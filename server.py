from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import mimetypes
import random
import sys
import hashlib

from app.ai_provider import ask_character, MODEL_NAME
from app.character_interaction import process_character_turn
from app.characters.characters_identity import CharacterIdentity, generate_identity
from app.characters.characters_profile import generate_character_profile, profile_to_dict
from app.characters.character_from_description import generate_character_from_description
from app.characters.characters_races import get_available_races
from app.characters.characters_languages import (
    CharacterLanguage,
    get_available_languages,
    get_language,
    get_race_languages,
)
from app.database.characters_db import (
    init_database,
    save_character,
    get_character,
    get_all_identities,
    delete_character,
)

HOST = "127.0.0.1"
PORT = 8000
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"

STAT_NAMES = (
    "strength", "constitution", "agility", "intelligence",
    "perception", "willpower", "charisma", "luck",
)

RACE_STAT_BIASES = {
    "umano": {"charisma": 2, "luck": 2, "intelligence": 1},
    "elfo": {"agility": 3, "intelligence": 3, "perception": 2, "constitution": -2},
    "nano": {"strength": 3, "constitution": 4, "agility": -2, "charisma": -1},
    "orco": {"strength": 5, "constitution": 3, "intelligence": -2, "charisma": -1},
    "demone": {"willpower": 4, "charisma": 3, "constitution": -1, "luck": 1},
    "draconide": {"strength": 3, "constitution": 3, "willpower": 2, "agility": -2},
    "mezzelfo": {"agility": 2, "charisma": 2, "intelligence": 2, "constitution": -1},
}

RACE_ABILITIES = {
    "umano": [("Adattabilità", "Impara rapidamente procedure e comportamenti nuovi, senza eccellere automaticamente in un singolo campo.")],
    "elfo": [("Sensi elfici", "Percepisce con maggiore facilità piccoli dettagli visivi e sonori nell'ambiente."), ("Affinità arcana", "Ha una predisposizione naturale verso la comprensione della magia, se questa viene studiata.")],
    "nano": [("Costituzione robusta", "Sopporta meglio fatica, freddo e condizioni fisiche difficili."), ("Occhio per la lavorazione", "Riconosce con relativa facilità difetti e qualità nei materiali lavorati.")],
    "orco": [("Fisico possente", "Dispone di una forza fisica naturale superiore alla media."), ("Resistenza brutale", "Può continuare uno sforzo fisico anche quando la fatica comincia a pesare.")],
    "demone": [("Presenza innaturale", "La sua presenza può risultare intensa o inquietante per chi non è abituato alla sua razza."), ("Sensibilità magica", "Percepisce più facilmente alcune manifestazioni magiche vicine.")],
    "draconide": [("Retaggio draconico", "Possiede tratti fisici draconici che possono influire sulle sue capacità corporee."), ("Resistenza naturale", "La costituzione draconica gli permette di sopportare meglio alcuni stress fisici.")],
    "mezzelfo": [("Versatilità", "Si adatta con relativa facilità a contesti culturali differenti."), ("Sensi affinati", "Può cogliere dettagli che sfuggono facilmente a persone meno attente.")],
}

RACE_SKILLS = {
    "umano": ["Orientamento", "Comunicazione", "Problem solving", "Lavoro pratico"],
    "elfo": ["Percezione ambientale", "Erboristeria", "Conoscenza della natura", "Studio arcano"],
    "nano": ["Fabbro", "Mineralogia", "Artigianato", "Resistenza al lavoro"],
    "orco": ["Sopravvivenza", "Caccia", "Combattimento fisico", "Intimidazione"],
    "demone": ["Percezione magica", "Conoscenza occulta", "Persuasione", "Sopravvivenza"],
    "draconide": ["Percezione", "Combattimento", "Sopravvivenza", "Conoscenza draconica"],
    "mezzelfo": ["Diplomazia", "Esplorazione", "Percezione", "Conoscenza culturale"],
}


def json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionAbortedError):
        pass


def identity_to_dict(identity, character_id=None):
    result = {
        "name": identity.name, "surname": identity.surname, "nickname": identity.nickname,
        "age": identity.age, "birth_date": identity.birth_date, "sex": identity.sex,
        "race": identity.race, "physical_description": identity.physical_description,
        "appearance": identity.appearance,
    }
    if character_id is not None:
        result["id"] = character_id
    return result


def language_to_dict(language):
    return {
        "language_id": language.language_id, "name": language.name,
        "comprehension": language.comprehension, "speaking": language.speaking,
        "writing": language.writing,
    }


def identity_from_dict(data):
    if not isinstance(data, dict):
        raise ValueError("I dati del personaggio devono essere un oggetto JSON.")
    identity = CharacterIdentity(
        name=str(data.get("name", "")).strip(), surname=str(data.get("surname", "")).strip(),
        nickname=str(data.get("nickname", "")).strip(), age=int(data.get("age", 0)),
        birth_date=str(data.get("birth_date", "")).strip(), sex=str(data.get("sex", "")).strip(),
        race=str(data.get("race", "")).strip(), physical_description=str(data.get("physical_description", "")).strip(),
        appearance=str(data.get("appearance", "")).strip(),
    )
    from app.characters.characters_identity import validate_identity
    validate_identity(identity_to_dict(identity))
    return identity


def languages_from_dict(data):
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        language_name = str(item.get("name", "")).strip()
        world_language = get_language(language_name)
        if world_language is None:
            raise ValueError(f"Lingua non disponibile: {language_name}")
        result.append(CharacterLanguage(
            language_id=world_language.id,
            name=world_language.name,
            comprehension=float(item.get("comprehension", 0.0)),
            speaking=float(item.get("speaking", 0.0)),
            writing=float(item.get("writing", 0.0)),
        ))
    return result


def character_to_dict(character):
    return {
        "id": character["id"],
        "identity": identity_to_dict(character["identity"], character["id"]),
        "languages": [language_to_dict(language) for language in character["languages"]],
        "psychology": character.get("extra", {}).get("psychology", {}),
        "personality": character.get("extra", {}).get("personality", {}),
        "extra": character.get("extra", {}),
    }


def generate_statistics(race_name):
    race_key = race_name.strip().lower()
    bias = RACE_STAT_BIASES.get(race_key, {})
    ranks = [random.randint(30, 72) for _ in STAT_NAMES]
    ranks.sort(reverse=True)
    random.shuffle(ranks)
    stats = {}
    for index, name in enumerate(STAT_NAMES):
        value = ranks[index] + random.randint(-6, 6) + bias.get(name, 0)
        stats[name] = max(5, min(95, value))
    primary = random.choice(list(bias.keys()) or list(STAT_NAMES))
    secondary = random.choice([name for name in STAT_NAMES if name != primary])
    stats[primary] = min(95, stats[primary] + random.randint(4, 10))
    stats[secondary] = min(95, stats[secondary] + random.randint(2, 6))
    return stats


def generate_extra(identity, profile, source="system", description="", importance="major"):
    race = identity.race.strip().lower()
    stats = generate_statistics(identity.race)
    max_health = 70 + stats["constitution"] * 2 + stats["strength"] // 2
    max_stamina = 50 + stats["constitution"] + stats["agility"]
    max_mana = 20 + stats["intelligence"] + stats["willpower"]
    abilities = RACE_ABILITIES.get(race, [])[:]
    random.shuffle(abilities)
    abilities = [{"name": name, "description": description} for name, description in abilities[:random.randint(0, min(2, len(abilities)))]]
    skill_names = RACE_SKILLS.get(race, ["Osservazione", "Sopravvivenza", "Comunicazione"])
    random.shuffle(skill_names)
    skills = [{"name": name, "description": f"Competenza pratica sviluppata dal personaggio nell'ambito di {name.lower()}."} for name in skill_names[:random.randint(1, min(3, len(skill_names)))]]
    return {
        "statistics": stats,
        "abilities": abilities,
        "skills": skills,
        "conditions": {"health": max_health, "stamina": max_stamina, "mana": max_mana, "status": "Normale"},
        "relationships": [],
        "psychology": {key: value for key, value in profile.items() if key in {"mental_state", "emotional_stability", "fears", "desires", "values", "traumas"}},
        "personality": {key: value for key, value in profile.items() if key in {"personality_description", "traits", "strengths", "flaws", "habits", "social_behavior"}},
        "generation": {"source": source, "importance": importance, "description": description},
    }


def build_generated_character(identity, source="system", description="", importance="major"):
    profile = profile_to_dict(generate_character_profile(identity_to_dict(identity)))
    languages = get_race_languages(identity.race)
    extra = generate_extra(identity, profile, source, description, importance)
    return {
        "identity": identity_to_dict(identity),
        "languages": [language_to_dict(language) for language in languages],
        "psychology": extra["psychology"],
        "personality": extra["personality"],
        "extra": extra,
    }


def generate_character(description="", source="system", importance="major"):
    description = str(description or "").strip()
    if description:
        identity = generate_character_from_description(description)
    else:
        races = get_available_races()
        if not races:
            raise ValueError("Non sono presenti razze disponibili.")
        weights = [max(0.0, float(race.rarity)) for race in races]
        race = random.choices(races, weights=weights if any(weights) else None, k=1)[0]
        identity = generate_identity(race.name)
    return build_generated_character(identity, source, description, importance)


class RPGServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[SERVER] {self.address_string()} - {format % args}")

    def do_OPTIONS(self):
        json_response(self, {"success": True})

    def do_GET(self):
        try:
            request_path = self.path.split("?", 1)[0].rstrip("/") or "/"
            if request_path == "/api/races":
                json_response(self, [{"id": race.id, "name": race.name, "description": race.description, "average_height": race.average_height, "average_weight": race.average_weight, "lifespan": race.lifespan, "rarity": race.rarity} for race in get_available_races()])
                return
            if request_path == "/api/languages":
                json_response(self, [{"id": language.id, "name": language.name, "prevalence": language.prevalence, "difficulty": language.difficulty} for language in get_available_languages()])
                return
            if request_path == "/api/characters":
                json_response(self, get_all_identities())
                return
            if request_path.startswith("/api/characters/"):
                character_id = int(request_path.rsplit("/", 1)[1])
                character = get_character(character_id)
                if character is None:
                    json_response(self, {"error": "Personaggio non trovato."}, 404)
                    return
                if not character["languages"]:
                    character["languages"] = get_race_languages(character["identity"].race)
                json_response(self, character_to_dict(character))
                return
            if request_path == "/api/ai-status":
                provider_path = Path(__file__).resolve().parent / "app" / "ai_provider.py"
                code_hash = hashlib.sha256(provider_path.read_bytes()).hexdigest()[:12] if provider_path.exists() else "missing"
                json_response(self, {
                    "model": MODEL_NAME,
                    "provider_file": str(provider_path),
                    "provider_hash": code_hash,
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
                data = self.read_json()
                description = data.get("description", "")
                source = data.get("source", "system")
                importance = data.get("importance", "major")
                json_response(self, generate_character(description, source, importance))
                return

            if request_path == "/api/character-interaction":
                data = self.read_json()
                character_id = int(data.get("character_id"))
                player_input = str(data.get("message", "")).strip()
                if not player_input:
                    raise ValueError("Il messaggio non può essere vuoto.")
                result = process_character_turn(
                    character_id,
                    player_input,
                    data.get("recent_conversation", []),
                )
                json_response(self, result)
                return

            if request_path == "/api/characters":
                data = self.read_json()
                identity = identity_from_dict(data.get("identity", data))
                languages = languages_from_dict(data.get("languages", [])) or get_race_languages(identity.race)
                extra = data.get("extra", {})
                if not isinstance(extra, dict):
                    extra = {}
                character_id = data.get("id")
                if character_id is None or str(character_id).strip() == "":
                    character_id = save_character(identity, languages, extra_data=extra)
                    print(f"[DATABASE] Personaggio creato: ID {character_id}")
                else:
                    character_id = save_character(identity, languages, extra_data=extra, character_id=int(character_id))
                    print(f"[DATABASE] Personaggio aggiornato: ID {character_id}")
                json_response(self, {"success": True, "id": character_id, "identity": identity_to_dict(identity, character_id), "languages": [language_to_dict(language) for language in languages], "extra": extra})
                return

            if request_path == "/api/race-languages":
                data = self.read_json()
                race = data.get("race")
                if not isinstance(race, str) or not race.strip():
                    json_response(self, {"error": "Razza non specificata."}, 400)
                    return
                json_response(self, [language_to_dict(language) for language in get_race_languages(race)])
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
            json_response(self, {"error": str(error)}, 500

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            raise ValueError("Body JSON mancante.")
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("JSON della richiesta non valido.") from error
        if not isinstance(data, dict):
            raise ValueError("Il body JSON deve essere un oggetto.")
        return data

    def serve_frontend(self):
        relative = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        file_path = (FRONTEND_DIR / relative).resolve()
        if FRONTEND_DIR not in file_path.parents and file_path != FRONTEND_DIR:
            self.send_error(403)
            return
        if not file_path.exists() or not file_path.is_file():
            file_path = FRONTEND_DIR / "index.html"
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server():
    init_database()
    print("=" * 60)
    print("AI RPG SERVER")
    print(f"AI MODEL: {MODEL_NAME}")
    print("AI PROVIDER: app.ai_provider")
    print("AI STATUS: http://127.0.0.1:8000/api/ai-status")
    print("=" * 60)
    server = HTTPServer((HOST, PORT), RPGServer)
    print(f"Server avviato su http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer arrestato.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
