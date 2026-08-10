import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"
OLLAMA_TIMEOUT = 120
TEMPERATURE = 0.65
NUM_CTX = 16384


def ask_ollama(system_prompt, user_prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        # Il modello ha già il contratto JSON nello system prompt.
        # JSON mode è più compatibile con qwen3:30b-a3b-instruct-2507-q4_K_M
        # rispetto a imporre uno schema complesso direttamente a Ollama.
        "format": "json",
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
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("Ollama ha restituito una risposta priva di message.content valido.")
    return message["content"].strip()


def _subject_guidance(player_input: str) -> str:
    text = player_input.strip().lower()
    player_patterns = [
        r"\b(io|me|mi|mio|mia|miei|mie|ho|sono|ero|avevo|facevo|feci)\b",
        r"\bl['’]\s*ho\b",
    ]
    character_patterns = [
        r"\b(tu|te|ti|tuo|tua|tuoi|tue|hai|sei|eri|avevi|facevi|fai)\b",
        r"\bl['’]\s*hai\b",
    ]
    player_match = any(re.search(pattern, text) for pattern in player_patterns)
    character_match = any(re.search(pattern, text) for pattern in character_patterns)
    if player_match and character_match:
        return "PRIMA PERSONA = PLAYER; SECONDA PERSONA = CURRENT_CHARACTER. Mantieni i soggetti separati."
    if player_match:
        return "PRIMA PERSONA = PLAYER. Non attribuire l'azione a CURRENT_CHARACTER."
    if character_match:
        return "SECONDA PERSONA = CURRENT_CHARACTER. Non attribuire l'azione al PLAYER."
    return "Nessun soggetto personale esplicito: non inventare chi ha compiuto l'azione."


def build_ai_context(character_context):
    if not isinstance(character_context, dict):
        raise ValueError("character_context deve essere un dizionario.")
    character = character_context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene un personaggio valido.")
    roles = character_context.get("roles", {})
    if not isinstance(roles, dict):
        roles = {}
    player = roles.get("player", {})
    current_character = roles.get("current_character", character)
    if not isinstance(player, dict):
        player = {}
    if not isinstance(current_character, dict):
        current_character = character

    def safe_list(key):
        value = character_context.get(key, [])
        return value if isinstance(value, list) else []

    state = character_context.get("state", {})
    if not isinstance(state, dict):
        state = {}
    scene = character_context.get("scene", {})
    if not isinstance(scene, dict):
        scene = {}

    return {
        "roles": {"PLAYER": player, "CURRENT_CHARACTER": current_character},
        "character": character,
        "state": state,
        "memories": safe_list("memories"),
        "relationships": safe_list("relationships"),
        "characters_present": safe_list("characters_present"),
        "scene": {
            "player": player,
            "reacting_character_id": scene.get("reacting_character_id"),
            "player_id": scene.get("player_id"),
            "involved_characters": scene.get("involved_characters", []),
        },
        "recent_conversation": safe_list("recent_conversation"),
        "recent_events": safe_list("recent_events"),
        "continuity_facts": safe_list("continuity_facts"),
    }


def _parse_ai_json(response: str) -> dict:
    """Parse JSON prodotto da Qwen, tollerando eventuali wrapper comuni senza inventare testo."""
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        # Alcune risposte possono contenere testo prima/dopo l'oggetto JSON.
        match = re.search(r"\{.*\}", response, flags=re.DOTALL)
        if not match:
            raise ValueError(f"Qwen non ha restituito JSON valido: {response[:500]}")
        try:
            result = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            raise ValueError(f"Qwen ha restituito JSON non interpretabile: {response[:500]}") from error

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError as error:
            raise ValueError(f"Qwen ha restituito una stringa invece del JSON del game engine: {response[:500]}") from error

    if not isinstance(result, dict):
        raise ValueError(f"La risposta AI deve essere un oggetto JSON: {response[:500]}")
    return result


def ask_character(character_context, player_input):
    if not isinstance(character_context, dict):
        raise ValueError("character_context deve essere un dizionario.")
    if not isinstance(player_input, str) or not player_input.strip():
        raise ValueError("player_input non può essere vuoto.")

    character = character_context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene un personaggio valido.")
    character_id = character.get("id")
    character_name = character.get("name")
    if not isinstance(character_id, int) or not isinstance(character_name, str):
        raise ValueError("Il personaggio non contiene un ID o nome valido.")

    state = character_context.get("state", {})
    if not isinstance(state, dict):
        state = {}
    current_goal = state.get("goal", "") if isinstance(state.get("goal", ""), str) else ""

    ai_context = build_ai_context(character_context)
    context_json = json.dumps(ai_context, indent=2, ensure_ascii=False, default=str)
    roles = ai_context["roles"]
    player_id = roles["PLAYER"].get("id")
    player_name = roles["PLAYER"].get("name") or "Giocatore"
    subject_lock = _subject_guidance(player_input)

    system_prompt = f"""
Sei {character_name}, personaggio di un RPG narrativo persistente.

IDENTITÀ ASSOLUTE
CURRENT_CHARACTER = {character_name} (ID {character_id}).
PLAYER = la persona che gioca (ID {player_id}, nome {player_name}).
Sono entità diverse. Tu interpreti esclusivamente CURRENT_CHARACTER.
Non decidere mai azioni, pensieri, emozioni, intenzioni o ricordi del PLAYER.

ATTRIBUZIONE DEL SOGGETTO
- io, me, mi, mio/mia, ho, sono, ero, avevo, facevo, l'ho = PLAYER.
- tu, te, ti, tuo/tua, hai, sei, eri, avevi, facevi, fai, l'hai = CURRENT_CHARACTER.
- terza persona = soggetto nominato.
Il messaggio attuale ha priorità nell'attribuzione grammaticale.
Una memoria o un evento precedente NON può cambiare il soggetto della frase attuale.

Esempi:
Io ho ucciso il drago -> PLAYER ha ucciso il drago.
Hai ucciso il drago? -> domanda su CURRENT_CHARACTER.
Perché l'ho fatto? -> soggetto PLAYER.
Perché l'hai fatto? -> soggetto CURRENT_CHARACTER.

CONTINUITÀ
Memorie, eventi e continuity_facts sono fatti persistenti. Non modificarli solo per rendere elegante la risposta.
Se il PLAYER afferma qualcosa che contraddice un fatto persistente, trattalo come possibile nuova informazione o contraddizione.
Non inventare fatti mancanti.

CONOSCENZA
Conosci solo ciò che CURRENT_CHARACTER può conoscere dal contesto. Non sei onnisciente.

STILE
Rispondi normalmente come {character_name}. Non aggiungere automaticamente misteri, combattimenti o lore.

OUTPUT OBBLIGATORIO
Restituisci ESCLUSIVAMENTE un singolo oggetto JSON:
{{
  "narration": "risposta parlata di {character_name}",
  "actions": [
    {{
      "type": "character_reaction",
      "character_id": {character_id},
      "emotion": "emozione",
      "thought": "pensiero di {character_name}",
      "intention": "intenzione di {character_name}",
      "goal": "{current_goal}"
    }}
  ]
}}

REGOLE JSON:
- narration deve essere una stringa non vuota.
- actions deve contenere esattamente una character_reaction.
- character_reaction.character_id deve essere {character_id}.
- Non aggiungere campi al livello principale.
- Non mettere la risposta testuale dentro actions.
- Nessun markdown o testo fuori dal JSON.
""".strip()

    user_prompt = f"""
CONTESTO AUTOREVOLE DEL GAME ENGINE:
{context_json}

MESSAGGIO ATTUALE DEL PLAYER:
{player_input.strip()}

{subject_lock}

Rispondi direttamente al PLAYER come {character_name}. Restituisci solo il JSON richiesto.
""".strip()

    response = ask_ollama(system_prompt, user_prompt)
    result = _parse_ai_json(response)

    narration = result.get("narration")
    actions = result.get("actions")

    # Compatibilità con eventuali wrapper prodotti da modelli/versioni precedenti.
    if not isinstance(narration, str) or not narration.strip():
        for key in ("response", "text", "content"):
            candidate = result.get(key)
            if isinstance(candidate, str) and candidate.strip():
                result["narration"] = candidate.strip()
                narration = result["narration"]
                break

    if not isinstance(narration, str) or not narration.strip():
        raise ValueError(f"La risposta AI non contiene una narration valida. Risposta ricevuta: {response[:500]}")

    if not isinstance(actions, list):
        raise ValueError(f"La risposta AI non contiene un array actions valido. Risposta ricevuta: {response[:500]}")

    # Se Qwen ha omesso character_reaction, aggiungiamo solo la struttura minima
    # deterministica necessaria al game engine; non inventiamo una nuova narrazione.
    reactions = [a for a in actions if isinstance(a, dict) and a.get("type") == "character_reaction"]
    if not reactions:
        actions.insert(0, {
            "type": "character_reaction",
            "character_id": character_id,
            "emotion": "neutral",
            "thought": "",
            "intention": "",
            "goal": current_goal,
        })
        result["actions"] = actions

    return json.dumps(result, ensure_ascii=False)
