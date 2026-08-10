from __future__ import annotations

import json
import re
from typing import Any

import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"
OLLAMA_TIMEOUT = 120
TEMPERATURE = 0.8
NUM_CTX = 16384
MAX_RECENT_NARRATIONS = 8
MAX_ERROR_PREVIEW = 1000


def _preview(value: Any, limit: int = MAX_ERROR_PREVIEW) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def ask_ollama(system_prompt: str, user_prompt: str) -> str:
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt non può essere vuoto.")
    if not isinstance(user_prompt, str) or not user_prompt.strip():
        raise ValueError("user_prompt non può essere vuoto.")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX},
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
    except requests.Timeout as error:
        raise ValueError("Timeout durante la comunicazione con Ollama.") from error
    except requests.RequestException as error:
        status = getattr(error.response, "status_code", None)
        if status is not None:
            detail = _preview(getattr(error.response, "text", ""))
            raise ValueError(f"Ollama HTTP {status}: {detail}") from error
        raise ValueError("Errore durante la comunicazione con Ollama.") from error

    try:
        data = response.json()
    except ValueError as error:
        raise ValueError("Ollama ha restituito una risposta HTTP non interpretabile come JSON.") from error

    message = data.get("message")
    if not isinstance(message, dict):
        raise ValueError(f"Risposta Ollama senza message valido: {_preview(data)}")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"Ollama ha restituito message.content vuoto: {_preview(data)}")
    return content.strip()


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_ai_context(character_context: dict[str, Any]) -> dict[str, Any]:
    """Riduce e normalizza il contesto mantenendo il confine del personaggio."""
    if not isinstance(character_context, dict):
        raise ValueError("character_context deve essere un dizionario.")

    character = character_context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene un personaggio valido.")

    roles = _safe_dict(character_context.get("roles"))
    player = _safe_dict(roles.get("player"))
    current_character = roles.get("current_character")
    if not isinstance(current_character, dict):
        current_character = character

    state = _safe_dict(character_context.get("state"))
    scene = _safe_dict(character_context.get("scene"))
    scope = _safe_dict(character_context.get("context_scope"))

    character_id = character.get("id")
    if scope.get("character_id") not in (None, character_id):
        raise ValueError("Il context_scope non corrisponde al personaggio corrente.")

    memories = [
        item for item in _safe_list(character_context.get("memories"))
        if not isinstance(character_id, int) or not isinstance(item, dict)
        or item.get("character_id") == character_id
    ]
    events = [
        item for item in _safe_list(character_context.get("recent_events"))
        if not isinstance(character_id, int) or not isinstance(item, dict)
        or item.get("character_id") == character_id
    ]

    return {
        "context_scope": {
            "character_id": character_id,
            "memory_scope": scope.get("memory_scope", f"ONLY_CHARACTER_{character_id}"),
            "event_scope": scope.get("event_scope", f"ONLY_CHARACTER_{character_id}"),
            "conversation_scope": scope.get("conversation_scope", f"ONLY_CHARACTER_{character_id}"),
        },
        "roles": {
            "PLAYER": player,
            "CURRENT_CHARACTER": current_character,
        },
        "character": character,
        "state": state,
        "memories": memories,
        "relationships": _safe_list(character_context.get("relationships")),
        "characters_present": _safe_list(character_context.get("characters_present")),
        "scene": {
            "player": player,
            "reacting_character_id": scene.get("reacting_character_id"),
            "player_id": scene.get("player_id"),
            "involved_characters": _safe_list(scene.get("involved_characters")),
        },
        "recent_conversation": _safe_list(character_context.get("recent_conversation")),
        "recent_events": events,
        "continuity_facts": _safe_list(character_context.get("continuity_facts")),
    }


def _recent_narrations(character_context: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for item in _safe_list(character_context.get("recent_conversation")):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).lower()
        text = item.get("content", item.get("message", item.get("text", "")))
        if role in {"assistant", "character", "npc", "current_character"} and isinstance(text, str) and text.strip():
            values.append(text.strip())
    return values[-MAX_RECENT_NARRATIONS:]


def _normalize_for_comparison(text: str) -> str:
    """Normalizza una risposta solo per individuare duplicati evidenti."""
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).strip(" .!?\"'“”‘’")


def _is_duplicate_narration(narration: str, previous: list[str]) -> bool:
    normalized = _normalize_for_comparison(narration)
    if not normalized:
        return False
    return any(normalized == _normalize_for_comparison(item) for item in previous if isinstance(item, str))


def _parse_ai_result(response: str) -> dict[str, Any]:
    try:
        result = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError(f"Ollama ha restituito JSON non valido: {_preview(response)}") from error

    if not isinstance(result, dict):
        raise ValueError("La risposta AI deve essere un oggetto JSON.")

    narration = result.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        reaction = result.get("character_reaction")
        if isinstance(reaction, dict):
            narration = reaction.get("narration")

    if not isinstance(narration, str) or not narration.strip():
        raise ValueError(f"La risposta AI non contiene una narration valida. Risposta ricevuta: {_preview(response)}")

    actions = result.get("actions")
    if not isinstance(actions, list):
        reaction = result.get("character_reaction")
        actions = [reaction] if isinstance(reaction, dict) else []

    result["narration"] = narration.strip()
    result["actions"] = actions
    return result


def ask_character(character_context: dict[str, Any], player_input: str) -> str:
    """Genera il turno del personaggio corrente, senza condividere memoria tra NPC."""
    if not isinstance(character_context, dict):
        raise ValueError("character_context deve essere un dizionario.")

    player_input = str(player_input or "").strip()
    if not player_input:
        raise ValueError("player_input non può essere vuoto.")

    character = character_context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene un personaggio valido.")

    character_id = character.get("id")
    character_name = character.get("name")
    if not isinstance(character_id, int) or not isinstance(character_name, str) or not character_name.strip():
        raise ValueError("Il personaggio non contiene un ID o nome valido.")

    scope = _safe_dict(character_context.get("context_scope"))
    if scope.get("character_id") != character_id:
        raise ValueError("Il contesto AI non è isolato dal personaggio corrente.")

    state = _safe_dict(character_context.get("state"))
    current_goal = state.get("goal", "")
    if not isinstance(current_goal, str):
        current_goal = ""

    ai_context = build_ai_context(character_context)
    context_json = json.dumps(ai_context, indent=2, ensure_ascii=False, default=str)

    player = ai_context["roles"]["PLAYER"]
    player_id = player.get("id")
    player_name = player.get("name") or "Giocatore"
    recent_narrations = _recent_narrations(character_context)
    repetition_block = "\n".join(f"- {text}" for text in recent_narrations) if recent_narrations else "(nessuna risposta precedente disponibile)"

    system_prompt = f"""
Sei {character_name}, personaggio di un RPG narrativo persistente.

CONFINE DI CONOSCENZA ASSOLUTO
Stai interpretando esclusivamente CURRENT_CHARACTER {character_name} con ID {character_id}.
Il contesto contiene solo memoria, eventi e conversazione autorizzati per questo personaggio.
Non usare mai memoria, conversazione o eventi appartenenti a un altro personaggio.
Se un'informazione non è presente nella memoria, negli eventi, nella conversazione corrente o nel mondo esplicitamente fornito, NON sai quell'informazione.
Non dedurre che un altro NPC sappia qualcosa solo perché è presente nel sistema.
Non inventare ricordi per colmare un vuoto.
Se PLAYER chiede qualcosa che {character_name} non può sapere, rispondi naturalmente che non lo sa, oppure chiedi spiegazioni.

IDENTITÀ ASSOLUTE
CURRENT_CHARACTER = {character_name} (ID {character_id}).
PLAYER = la persona che gioca (ID {player_id}, nome {player_name}).
Sono due entità distinte. Tu interpreti esclusivamente CURRENT_CHARACTER.
Non decidere mai azioni, pensieri, emozioni, intenzioni o ricordi del PLAYER.

RISOLUZIONE DEI RIFERIMENTI DEL PLAYER
Prima di rispondere, determina sempre a quale entità si riferiscono i pronomi e le forme verbali del messaggio del PLAYER.
Quando il PLAYER dice "io", "me", "mi", "mio", "mia", "miei", "mie", "sono", "ero", "avevo", "ho", "vivevo", "sono nato", "sono cresciuto", "ho fatto" o formule equivalenti riferite a sé, il soggetto è SEMPRE PLAYER.
Quando il PLAYER dice "tu", "te", "ti", "tuo", "tua", "tuoi", "tue", "sei", "eri", "avevi", "hai", "vivevi", "hai fatto" o formule equivalenti riferite all'interlocutore, il referente è CURRENT_CHARACTER.
Questa regola vale anche nelle DOMANDE. Esempio: "Sai dove sono nato?" significa "Sai dove è nato il PLAYER?", NON "Sai dove sei nato tu?".
Esempio: "Ti avevo mai detto dove sono nato?" significa "Ti avevo già comunicato il luogo di nascita del PLAYER?".
Esempio: "Ricordi dove vivevo da bambino?" significa "Ricordi dove viveva il PLAYER da bambino?".
Esempio: "Dove sei nato?" significa "Qual è il luogo di nascita di CURRENT_CHARACTER?".
Non sostituire mai automaticamente PLAYER con CURRENT_CHARACTER solo perché il messaggio usa la prima persona.
Non trasferire mai un fatto da PLAYER a CURRENT_CHARACTER o viceversa.
Se il soggetto non può essere determinato con sicurezza, non inventare: chiedi chiarimento oppure rispondi senza attribuire il fatto.

ATTRIBUZIONE DELLA FONTE DELLE INFORMAZIONI
Devi distinguere sempre tra "chi conosce un'informazione" e "chi ha comunicato quell'informazione".
Se una memoria o un evento indica che PLAYER ha raccontato qualcosa a {character_name}, allora PLAYER è la fonte e {character_name} è il destinatario.
In questo caso NON dire mai "te l'ho detto", "te l'avevo detto" o formule equivalenti riferite a quel fatto.
Usa invece formulazioni naturali come "me l'hai detto", "me l'avevi detto", "mi avevi raccontato", "ricordo che me l'avevi detto".
"Te l'ho detto" significa che {character_name} aveva precedentemente comunicato quell'informazione al PLAYER. Usalo solo quando il contesto dimostra realmente che la fonte era {character_name}.
Esempio: se PLAYER dice "Sono nato a Xalverun" e poi chiede "Sai dove sono nato?", una risposta corretta è "Xalverun. Me l'avevi detto poco fa." oppure semplicemente "Xalverun.".
Non aggiungere "te l'ho già detto" quando l'informazione è stata appresa dal PLAYER.

CONTINUITÀ
Memorie, eventi e continuity_facts sono fatti persistenti del personaggio corrente.
Non riscrivere il passato e non inventare fatti mancanti.
Una conversazione normale può rimanere normale: non aggiungere automaticamente misteri, combattimenti, lore o dramma.

CARATTERISTICHE VS ARGOMENTI
La personalità, i poteri, le passioni, i traumi, le abitudini e i simboli distintivi di {character_name} sono caratteristiche, non argomenti obbligatori.
Una caratteristica influenza il modo di reagire quando è pertinente, ma normalmente rimane sullo sfondo.
NON citare, nominare o usare in metafora una caratteristica soltanto perché esiste.
NON usare il potere o il tema più riconoscibile come risposta predefinita.
Se PLAYER cambia argomento, cambia argomento anche tu.
Se si parla di vita quotidiana, rispondi in modo quotidiano anche se possiedi magia, traumi o una storia particolare.
Un potere emerge quando la situazione lo rende pertinente; una passione emerge quando l'argomento la richiama; un trauma influenza una reazione quando qualcosa lo riattiva.

EVOLUZIONE NEL TEMPO
{character_name} parte dalla personalità di base definita nel contesto, ma non è una personalità congelata.
Le esperienze realmente vissute producono cambiamenti graduali nel modo di parlare, fidarsi, scherzare, aprirsi, reagire e comportarsi.
Usa memorie, eventi, relazioni e conversazioni precedenti per capire cosa {character_name} ha imparato dal PLAYER e dalla storia.
Il tempo passato insieme conta, ma il cambiamento deve emergere naturalmente dal comportamento.
Non cambiare drasticamente personalità dopo un singolo messaggio.
Le relazioni persistono anche quando non vengono nominate.

MEMORIA PERSISTENTE LEGGERA
La memoria non è il registro della conversazione.
Crea una memoria SOLO quando il turno contiene un fatto che vale la pena ricordare anche molto più avanti.
Se PLAYER dichiara esplicitamente un fatto personale stabile e utile per il futuro, considera la creazione di una memoria una priorità.
Esempio: se PLAYER dice "Da bambino vivevo nel villaggio di Valdombra", la memoria corretta è "Il PLAYER ha raccontato a {character_name} di aver vissuto a Valdombra durante l'infanzia.".
Non creare memoria per saluti, battute, domande comuni, dettagli casuali o normali scambi.
Al massimo crea UNA memoria nello stesso turno.
La memoria deve essere breve, concreta e basata solo su ciò che {character_name} ha realmente appreso.

NATURALITÀ E RIPETIZIONI
La risposta reagisce prima di tutto al messaggio appena ricevuto.
Evita tormentoni, metafore ricorrenti, formule ripetute e il continuo ritorno allo stesso tema.
Non ripetere la stessa immagine o concetto delle risposte precedenti se non è necessario.
Se PLAYER fa una domanda semplice, rispondi semplicemente.
Se PLAYER scherza, puoi scherzare.
Non trasformare ogni risposta in una frase poetica o misteriosa.

RISPOSTE PRECEDENTI DA EVITARE COME FORMULAZIONE
{repetition_block}
Usale solo per evitare ripetizioni. Non copiarne frasi, metafore o strutture.

OUTPUT
Restituisci ESATTAMENTE un singolo oggetto JSON:
{{
  "narration": "risposta parlata di {character_name}",
  "actions": [
    {{"type": "character_reaction", "character_id": {character_id}, "emotion": "emozione", "thought": "pensiero di {character_name}", "intention": "intenzione di {character_name}", "goal": "{current_goal}"}}
  ]
}}
Puoi aggiungere DOPO character_reaction una sola create_memory SOLO se necessaria:
{{"type": "create_memory", "character_id": {character_id}, "content": "fatto importante ricordato da {character_name}", "memory_type": "evento", "importance": 1-10, "secret": false}}
Non creare create_memory se non è necessaria.
"narration" è obbligatoria e contiene la risposta di {character_name} al PLAYER.
"actions" è obbligatorio e deve contenere esattamente una character_reaction valida.
Non mettere narration dentro actions e non restituire character_reaction come oggetto principale.
Rispondi esclusivamente con JSON valido.
""".strip()

    user_prompt = f"""
CONTESTO AUTOREVOLE DEL GAME ENGINE:
{context_json}

MESSAGGIO ATTUALE DEL PLAYER:
{player_input}

Rispondi direttamente al messaggio attuale del PLAYER come {character_name}.
La risposta deve essere naturale, pertinente e non ripetitiva.
Le caratteristiche del personaggio devono emergere solo quando pertinenti al contenuto della scena.
Il rapporto con PLAYER e le esperienze condivise devono influenzare gradualmente il comportamento, non diventare automaticamente l'argomento.
Valuta separatamente se il messaggio contiene un fatto abbastanza importante da meritare una memoria persistente.
Non controllare PLAYER, non inventare fatti e non usare informazioni che appartengono a un altro personaggio.
Se PLAYER chiede un'informazione che non è presente nel contesto autorizzato, non fingere di ricordarla.
Quando ricordi un fatto appreso dal PLAYER, attribuisci correttamente la fonte: non dire che {character_name} "lo ha detto" se in realtà lo ha raccontato il PLAYER.
Restituisci esclusivamente il JSON richiesto.
""".strip()

    response = ask_ollama(system_prompt, user_prompt)
    result = _parse_ai_result(response)

    # Difesa deterministica contro la ripetizione identica della risposta precedente.
    # Il prompt la scoraggia già, ma questa verifica impedisce che Ollama restituisca
    # due volte la stessa battuta anche quando il modello ignora l'istruzione.
    if _is_duplicate_narration(result["narration"], recent_narrations):
        retry_prompt = f"""
La narration appena generata è identica a una risposta già data:
"{result['narration']}"

Genera ORA una risposta diversa al messaggio del PLAYER.
Mantieni esattamente gli stessi fatti conosciuti e la stessa identità del personaggio.
NON ripetere la frase precedente.
NON usare formule equivalenti come "te l'ho già detto" se il fatto era stato comunicato dal PLAYER.
Puoi rispondere in modo molto breve, anche con una sola frase, purché sia naturale e diversa.
Restituisci esclusivamente lo stesso JSON richiesto, con narration e actions.
""".strip()
        retry_response = ask_ollama(system_prompt, f"{user_prompt}\n\n{retry_prompt}")
        retry_result = _parse_ai_result(retry_response)
        if not _is_duplicate_narration(retry_result["narration"], recent_narrations):
            result = retry_result

    return json.dumps(result, ensure_ascii=False)
