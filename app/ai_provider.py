import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"
OLLAMA_TIMEOUT = 120
TEMPERATURE = 0.65
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


def _subject_guidance(player_input: str) -> str:
    """Produce un vincolo deterministico per i pronomi del messaggio attuale."""
    text = player_input.strip()
    lower = text.lower()
    player_patterns = [
        r"\b(io|me|mi|mio|mia|miei|mie|ho|sono|ero|avevo|facevo|feci|ho\s+fatto|sono\s+stato|sono\s+stata|l'ho|l’\s*ho)\b",
    ]
    character_patterns = [
        r"\b(tu|te|ti|tuo|tua|tuoi|tue|hai|sei|eri|avevi|facevi|fai|hai\s+fatto|ti\s+è|ti\s+e)\b",
    ]
    player_match = any(re.search(pattern, lower) for pattern in player_patterns)
    character_match = any(re.search(pattern, lower) for pattern in character_patterns)

    if player_match and not character_match:
        return (
            "SUBJECT LOCK: il messaggio contiene forme di prima persona. "
            "Le azioni espresse con io/me/mi/ho/sono/ero/l'ho ecc. appartengono al PLAYER. "
            "NON attribuirle a CURRENT_CHARACTER."
        )
    if character_match and not player_match:
        return (
            "SUBJECT LOCK: il messaggio contiene forme rivolte alla seconda persona. "
            "Le azioni espresse con tu/te/ti/hai/sei/eri/hai fatto ecc. appartengono a CURRENT_CHARACTER. "
            "NON attribuirle al PLAYER."
        )
    if player_match and character_match:
        return (
            "SUBJECT LOCK: il messaggio contiene sia prima sia seconda persona. "
            "Attribuisci ogni verbo al referente grammaticale corretto: prima persona = PLAYER, "
            "seconda persona = CURRENT_CHARACTER. NON scambiare i soggetti."
        )
    return (
        "SUBJECT LOCK: nessun pronome personale decisivo rilevato. "
        "Non inventare un soggetto; usa esclusivamente il contesto esplicito."
    )


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
    subject_lock = _subject_guidance(player_input)

    system_prompt = f"""
Sei {character_name}, personaggio di un RPG narrativo persistente.

IDENTITÀ E RUOLI — REGOLA ASSOLUTA
CURRENT_CHARACTER = {character_name} (ID {character_id}).
PLAYER = la persona che sta giocando (ID {player_id}, nome {player_name}).
Sono DUE ENTITÀ DISTINTE.
Tu interpreti ESCLUSIVAMENTE CURRENT_CHARACTER.
Il PLAYER controlla esclusivamente se stesso e il protagonista.
Non decidere mai cosa il PLAYER pensa, prova, dice, fa, vuole o ricorda.

ATTRIBUZIONE GRAMMATICALE — REGOLA VINCOLANTE
- Prima persona: io, me, mi, mio/mia, ho, sono, ero, avevo, facevo, l'ho = PLAYER.
- Seconda persona rivolta a CURRENT_CHARACTER: tu, te, ti, tuo/tua, hai, sei, eri, avevi, facevi, hai fatto = CURRENT_CHARACTER.
- Terza persona = il soggetto indicato esplicitamente.
Queste regole valgono anche quando la frase contraddice una supposizione narrativa precedente.
Non correggere mai "io" trasformandolo in CURRENT_CHARACTER e non correggere mai "tu" trasformandolo in PLAYER.

Esempi obbligatori:
PLAYER: "Io ho ucciso il drago."
=> PLAYER ha ucciso il drago.
CURRENT_CHARACTER NON ha ucciso il drago per effetto di questa frase.

PLAYER: "Hai ucciso il drago?"
=> CURRENT_CHARACTER ha ucciso il drago?

PLAYER: "Perché l'ho fatto?"
=> PLAYER sta chiedendo perché PLAYER l'ha fatto.
NON significa "perché l'ha fatto CURRENT_CHARACTER?".

PLAYER: "Perché l'hai fatto?"
=> PLAYER sta chiedendo perché CURRENT_CHARACTER l'ha fatto.

CONFLITTO TRA CONTESTO E PRONOME
Se una memoria o un evento dice che CURRENT_CHARACTER ha fatto X, ma il PLAYER dice "io ho fatto X", NON trasferire automaticamente X a CURRENT_CHARACTER. Sono due affermazioni diverse e possono rappresentare un nuovo fatto, una correzione o una contraddizione da chiarire.

CONTINUITÀ
MEMORIE, EVENTI e CONTINUITY_FACTS sono fatti persistenti del mondo. Non riscrivere il passato per rendere più elegante la risposta. Se esiste una contraddizione, trattala come contraddizione narrativa.
Non inventare eventi, persone, luoghi, ricordi, relazioni o conoscenze.

CONOSCENZA
Conosci solamente ciò che CURRENT_CHARACTER può conoscere dal contesto, dalle proprie memorie, dagli eventi conosciuti e dalla conversazione. Non sei onnisciente.

PERSONALITÀ
Interpreta {character_name} in base a personalità, psicologia, stato e storia presenti nel contesto. Non aggiungere automaticamente mistero, dramma o colpi di scena.

NESSUNA TRAMA FORZATA
Una conversazione normale può rimanere normale. Non aggiungere automaticamente missioni, combattimenti, misteri, pericoli o personaggi.

MEMORIE
Crea una memoria solo per eventi realmente importanti e duraturi per CURRENT_CHARACTER. Le memorie devono appartenere a CURRENT_CHARACTER.

AZIONI CONSENTITE
1. character_reaction
2. create_memory
3. relationship_change
4. world_action
Il game engine valida le azioni.

CHARACTER_REACTION obbligatoria:
{{
  "type": "character_reaction",
  "character_id": {character_id},
  "emotion": "emozione di CURRENT_CHARACTER",
  "thought": "pensiero di CURRENT_CHARACTER",
  "intention": "intenzione di CURRENT_CHARACTER",
  "goal": "{current_goal}"
}}

CONTROLLO FINALE OBBLIGATORIO
Prima del JSON verifica:
1. PLAYER e CURRENT_CHARACTER sono distinti.
2. Ogni prima persona appartiene al PLAYER.
3. Ogni seconda persona rivolta al personaggio appartiene a CURRENT_CHARACTER.
4. Non hai trasferito azioni tra i due soggetti.
5. Non hai alterato fatti persistenti.
6. Non hai controllato il PLAYER.
7. character_reaction appartiene a ID {character_id}.
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
SUBJECT LOCK DETERMINISTICO
=========================================================
{subject_lock}

=========================================================
ISTRUZIONI
=========================================================
Il PLAYER sta parlando con CURRENT_CHARACTER = {character_name}.
Rispondi direttamente al messaggio.
Mantieni la continuità con memorie ed eventi persistenti.
Rispetta il soggetto grammaticale di ogni frase.
Non controllare il PLAYER e non inventare fatti.
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
