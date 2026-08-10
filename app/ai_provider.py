import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"
OLLAMA_TIMEOUT = 120
TEMPERATURE = 0.75
NUM_CTX = 16384


def ask_ollama(system_prompt, user_prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX},
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
    except requests.RequestException as error:
        raise ValueError("Errore durante la comunicazione con Ollama.") from error
    if not response.ok:
        raise ValueError(f"Ollama HTTP {response.status_code}: {response.text}")
    try:
        data = response.json()
    except ValueError as error:
        raise ValueError("Ollama ha restituito una risposta HTTP non interpretabile come JSON.") from error
    message = data.get("message")
    if not isinstance(message, dict):
        raise ValueError(f"Risposta Ollama senza message valido: {str(data)[:1000]}")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"Ollama ha restituito message.content vuoto: {str(data)[:1000]}")
    return content.strip()


def build_ai_context(character_context):
    character = character_context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene un personaggio valido.")
    roles = character_context.get("roles", {})
    if not isinstance(roles, dict): roles = {}
    player = roles.get("player", {})
    current_character = roles.get("current_character", character)
    if not isinstance(player, dict): player = {}
    if not isinstance(current_character, dict): current_character = character
    def safe_list(key):
        value = character_context.get(key, [])
        return value if isinstance(value, list) else []
    state = character_context.get("state", {})
    if not isinstance(state, dict): state = {}
    scene = character_context.get("scene", {})
    if not isinstance(scene, dict): scene = {}
    return {
        "roles": {"PLAYER": player, "CURRENT_CHARACTER": current_character},
        "character": character, "state": state,
        "memories": safe_list("memories"), "relationships": safe_list("relationships"),
        "characters_present": safe_list("characters_present"),
        "scene": {"player": player, "reacting_character_id": scene.get("reacting_character_id"), "player_id": scene.get("player_id"), "involved_characters": scene.get("involved_characters", [])},
        "recent_conversation": safe_list("recent_conversation"), "recent_events": safe_list("recent_events"),
        "continuity_facts": safe_list("continuity_facts"),
    }


def ask_character(character_context, player_input):
    if not isinstance(character_context, dict): raise ValueError("character_context deve essere un dizionario.")
    player_input = str(player_input or "").strip()
    if not player_input: raise ValueError("player_input non può essere vuoto.")
    character = character_context.get("character")
    if not isinstance(character, dict): raise ValueError("Il contesto non contiene un personaggio valido.")
    character_id = character.get("id")
    character_name = character.get("name")
    if not isinstance(character_id, int) or not isinstance(character_name, str): raise ValueError("Il personaggio non contiene un ID o nome valido.")
    state = character_context.get("state", {})
    if not isinstance(state, dict): state = {}
    current_goal = state.get("goal", "") if isinstance(state.get("goal", ""), str) else ""
    ai_context = build_ai_context(character_context)
    context_json = json.dumps(ai_context, indent=2, ensure_ascii=False, default=str)
    player = ai_context["roles"]["PLAYER"]
    player_id = player.get("id")
    player_name = player.get("name") or "Giocatore"

    system_prompt = f"""
Sei {character_name}, personaggio di un RPG narrativo persistente.

IDENTITÀ ASSOLUTE
CURRENT_CHARACTER = {character_name} (ID {character_id}).
PLAYER = la persona che gioca (ID {player_id}, nome {player_name}).
Sono due entità distinte. Tu interpreti esclusivamente CURRENT_CHARACTER.
Non decidere mai azioni, pensieri, emozioni, intenzioni o ricordi del PLAYER.

SOGGETTI
Quando il PLAYER usa io/me/mi/ho/sono/ero/facevo/ho fatto, il soggetto è PLAYER.
Quando il PLAYER usa tu/te/ti/hai/sei/eri/facevi/hai fatto, il referente è CURRENT_CHARACTER.
Non trasferire mai un fatto da PLAYER a CURRENT_CHARACTER o viceversa.
Le memorie e gli eventi persistenti non cambiano il soggetto della frase attuale.

CONTINUITÀ
Memorie, eventi e continuity_facts sono fatti persistenti. Non riscrivere il passato e non inventare fatti mancanti.
Conosci solo ciò che CURRENT_CHARACTER può conoscere.
Una conversazione normale può rimanere normale: non aggiungere automaticamente misteri, combattimenti o trama.

OUTPUT — REGOLA ASSOLUTA
Devi restituire ESATTAMENTE un singolo oggetto JSON di questo tipo:
{{
  "narration": "risposta parlata di {character_name}",
  "actions": [
    {{
      "type": "character_reaction",
      "character_id": {character_id},
      "emotion": "emozione di {character_name}",
      "thought": "pensiero di {character_name}",
      "intention": "intenzione di {character_name}",
      "goal": "{current_goal}"
    }}
  ]
}}

REGOLE OUTPUT
- "narration" è OBBLIGATORIA, è una stringa non vuota e contiene la risposta che {character_name} dice al PLAYER.
- "actions" è OBBLIGATORIO ed è un array.
- "character_reaction" è OBBLIGATORIA dentro actions e character_id deve essere {character_id}.
- Non mettere la narration dentro actions.
- Non restituire un character_reaction come oggetto principale.
- Non usare markdown o testo fuori dal JSON.

Rispondi esclusivamente con JSON valido.
""".strip()

    user_prompt = f"""
CONTESTO AUTOREVOLE DEL GAME ENGINE:
{context_json}

MESSAGGIO ATTUALE DEL PLAYER:
{player_input}

Il PLAYER sta parlando con CURRENT_CHARACTER = {character_name}.
Rispondi direttamente al messaggio. Mantieni la continuità. Non controllare il PLAYER. Non inventare fatti.
RICORDA: il livello principale DEVE contenere sia "narration" sia "actions". La risposta parlata va in "narration".
Restituisci esclusivamente il JSON richiesto.
""".strip()

    response = ask_ollama(system_prompt, user_prompt)
    try:
        result = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError(f"Ollama ha restituito JSON non valido: {response[:1000]}") from error
    if not isinstance(result, dict): raise ValueError("La risposta AI deve essere un oggetto JSON.")

    # Recupero difensivo per modelli che restituiscono la reaction al livello principale.
    narration = result.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        reaction = result.get("character_reaction")
        if isinstance(reaction, dict):
            narration = reaction.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError(f"La risposta AI non contiene una narration valida. Risposta ricevuta: {response[:1000]}")
    actions = result.get("actions")
    if not isinstance(actions, list):
        reaction = result.get("character_reaction")
        if isinstance(reaction, dict): actions = [reaction]
        else: actions = []
    result["narration"] = narration.strip()
    result["actions"] = actions
    return json.dumps(result, ensure_ascii=False)
