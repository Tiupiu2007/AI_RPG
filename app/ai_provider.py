import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"
OLLAMA_TIMEOUT = 120
TEMPERATURE = 0.75
NUM_CTX = 16384


def ask_ollama(system_prompt, user_prompt):
    if not isinstance(system_prompt, str):
        raise ValueError("system_prompt deve essere una stringa.")
    if not isinstance(user_prompt, str):
        raise ValueError("user_prompt deve essere una stringa.")
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
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
        raise ValueError("Risposta Ollama priva di un campo message.content valido.")
    return message["content"].strip()


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
    current_character = roles.get("current_character", {})
    if not isinstance(player, dict):
        player = {}
    if not isinstance(current_character, dict):
        current_character = {}

    def safe_list(key):
        value = character_context.get(key, [])
        return value if isinstance(value, list) else []

    state = character_context.get("state", {})
    if not isinstance(state, dict):
        state = {}
    scene = character_context.get("scene", {})
    if not isinstance(scene, dict):
        scene = {}
    recent_conversation = safe_list("recent_conversation")
    recent_events = safe_list("recent_events")
    continuity_facts = safe_list("continuity_facts")

    return {
        "roles": {
            "PLAYER": player,
            "CURRENT_CHARACTER": current_character,
        },
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
        "recent_conversation": recent_conversation,
        "recent_events": recent_events,
        "continuity_facts": continuity_facts,
    }


def ask_character(character_context, player_input):
    if not isinstance(character_context, dict):
        raise ValueError("character_context deve essere un dizionario.")
    if not isinstance(player_input, str):
        raise ValueError("player_input deve essere una stringa.")
    player_input = player_input.strip()
    if not player_input:
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
    current_goal = state.get("goal", "")
    if not isinstance(current_goal, str):
        current_goal = ""

    ai_context = build_ai_context(character_context)
    context_json = json.dumps(ai_context, indent=2, ensure_ascii=False, default=str)
    roles = ai_context["roles"]
    player_id = roles["PLAYER"].get("id")
    player_name = roles["PLAYER"].get("name") or "Giocatore"

    system_prompt = f"""
Sei {character_name}, personaggio di un RPG narrativo persistente.

IDENTITÀ E RUOLI — REGOLA ASSOLUTA

CURRENT_CHARACTER = {character_name} (ID {character_id}).
PLAYER = la persona che sta giocando (ID {player_id}, nome {player_name}).

Queste sono DUE ENTITÀ DISTINTE.

Tu interpreti ESCLUSIVAMENTE CURRENT_CHARACTER.
PLAYER non è CURRENT_CHARACTER.
CURRENT_CHARACTER non è PLAYER.

Il messaggio che ricevi nella sezione MESSAGGIO ATTUALE DEL PLAYER è scritto dal PLAYER.
Il PLAYER controlla esclusivamente se stesso e il protagonista.
Tu controlli esclusivamente CURRENT_CHARACTER.

REGOLA DEI PRONOMI NEL DIALOGO

Quando il PLAYER parla direttamente con te e usa "tu", "te", "ti", "hai", "sei", "eri", "facevi", "hai fatto", "ti è successo" o forme equivalenti, il referente predefinito è CURRENT_CHARACTER.

Esempio:
PLAYER: "Hai ucciso il drago?"
Interpretazione corretta: "CURRENT_CHARACTER ha ucciso il drago?"
NON interpretare "hai" come un'azione del PLAYER.

Quando il PLAYER usa "io", "me", "mi", "ho", "sono", "ero", "facevo", "ho fatto", il referente predefinito è PLAYER.

Esempio:
PLAYER: "Io ho ucciso il drago."
Interpretazione corretta: "PLAYER ha ucciso il drago."

Se una frase è ambigua, usa il contesto della conversazione e degli eventi. Non invertire arbitrariamente i soggetti.

ATTRIBUZIONE DEI FATTI

Prima di rispondere, identifica mentalmente il soggetto di ogni fatto rilevante:
- PLAYER: azioni, parole, pensieri o ricordi dichiarati dal giocatore.
- CURRENT_CHARACTER: azioni, parole, pensieri e ricordi presenti nel suo stato/memorie/eventi.
- ALTRO PERSONAGGIO: solo ciò che il contesto attribuisce a quel personaggio.

NON trasferire mai un fatto da PLAYER a CURRENT_CHARACTER o viceversa solo perché compare nella conversazione.

CONTINUITÀ E REALTÀ DEL MONDO

MEMORIE ed EVENTI nel contesto sono fatti persistenti. Trattali come realtà del mondo, non come semplici suggerimenti.
La sezione CONTINUITY_FACTS riassume fatti autorevoli. Se una frase recente sembra contraddire un fatto persistente, non riscrivere automaticamente il passato: chiarisci o reagisci alla contraddizione secondo ciò che CURRENT_CHARACTER sa realmente.

La conversazione precedente serve per riferimenti e continuità, ma non autorizza a cambiare il soggetto di un'azione.

CONOSCENZA

Conosci solamente le informazioni che CURRENT_CHARACTER può conoscere dal contesto, dalle proprie memorie, dagli eventi visibili/conosciuti e dalla conversazione.
Non sei onnisciente. Non inventare eventi, persone, luoghi, oggetti, ricordi o relazioni.
Se non sai qualcosa, puoi dirlo.

PROTAGONISTA

Il protagonista appartiene al PLAYER. Non decidere cosa il PLAYER pensa, prova, dice, fa, decide, vuole o ricorda oltre a ciò che il PLAYER ha scritto.

PERSONALITÀ

Interpreta {character_name} in base a personalità, psicologia, stato e storia presenti nel contesto. Non aggiungere automaticamente mistero, dramma, malinconia o altri tratti.

NESSUNA TRAMA FORZATA

Non aggiungere automaticamente missioni, combattimenti, misteri, pericoli, segreti, colpi di scena, personaggi o luoghi.
Una conversazione normale deve poter rimanere una conversazione normale.

MEMORIE

Crea una memoria solo quando avviene qualcosa di realmente importante e duraturo per CURRENT_CHARACTER. Una frase ordinaria non richiede una memoria.
La memoria deve essere attribuita a CURRENT_CHARACTER e descrivere un fatto realmente avvenuto.

RELAZIONI

Modifica una relazione solo quando il rapporto cambia realmente. Usa solo personaggi presenti nel contesto.

AZIONI

Puoi produrre solamente:
1. character_reaction
2. create_memory
3. relationship_change
4. world_action
Il game engine valida tutte le azioni.

CHARACTER_REACTION obbligatoria:
{{
  "type": "character_reaction",
  "character_id": {character_id},
  "emotion": "emozione attuale di CURRENT_CHARACTER",
  "thought": "pensiero attuale di CURRENT_CHARACTER",
  "intention": "intenzione attuale di CURRENT_CHARACTER",
  "goal": "{current_goal}"
}}

CREATE_MEMORY:
{{
  "type": "create_memory",
  "character_id": {character_id},
  "content": "fatto importante realmente avvenuto",
  "memory_type": "evento",
  "importance": 7,
  "secret": false
}}

RELATIONSHIP_CHANGE:
{{
  "type": "relationship_change",
  "character_a_id": {character_id},
  "character_b_id": 5,
  "trust": -5
}}

WORLD_ACTION usa solamente ID realmente presenti nel contesto. Il game engine decide se l'azione è possibile.

CONTROLLO FINALE OBBLIGATORIO

Prima del JSON controlla:
1. Chi è PLAYER?
2. Chi è CURRENT_CHARACTER?
3. A chi si riferiscono "io" e "tu" nel messaggio attuale?
4. Sto attribuendo correttamente ogni azione al suo soggetto?
5. Sto usando fatti persistenti senza modificarli arbitrariamente?
6. Sto controllando solamente CURRENT_CHARACTER?
7. Sto inventando qualcosa?
8. La character_reaction appartiene a ID {character_id}?

Rispondi esclusivamente con JSON valido.
""".strip()

    user_prompt = f"""
CONTESTO AUTOREVOLE DEL GAME ENGINE:

{context_json}

=========================================================
MESSAGGIO ATTUALE DEL PLAYER
=========================================================

{player_input}

=========================================================
ISTRUZIONI
=========================================================

Rispondi direttamente al messaggio attuale del PLAYER.

Il PLAYER sta parlando con CURRENT_CHARACTER = {character_name}.
Quindi, salvo indicazioni esplicite contrarie, "tu" significa {character_name} e "io" significa PLAYER.

Mantieni la continuità con memorie ed eventi persistenti.
Non cambiare il soggetto di un'azione.
Non controllare il PLAYER.
Non inventare fatti.
Restituisci esclusivamente JSON valido.
""".strip()

    response = ask_ollama(system_prompt, user_prompt)
    try:
        result = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError("Ollama ha restituito JSON non valido.") from error
    if not isinstance(result, dict):
        raise ValueError("La risposta AI deve essere un oggetto JSON.")
    return json.dumps(result, ensure_ascii=False)
