from __future__ import annotations

import json
from typing import Any

import requests


# Configurazione centralizzata del provider AI.
# Il modello resta esplicitamente quello concordato per il progetto.
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"
OLLAMA_TIMEOUT = 120
TEMPERATURE = 0.8
NUM_CTX = 16384
MAX_RECENT_NARRATIONS = 8
MAX_ERROR_PREVIEW = 1000


def _preview(value: Any, limit: int = MAX_ERROR_PREVIEW) -> str:
    """Restituisce una rappresentazione breve e sicura per gli errori."""
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def ask_ollama(system_prompt: str, user_prompt: str) -> str:
    """Invia una richiesta non-streaming a Ollama e restituisce il contenuto."""
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
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
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
        raise ValueError(
            "Ollama ha restituito una risposta HTTP non interpretabile come JSON."
        ) from error

    message = data.get("message")
    if not isinstance(message, dict):
        raise ValueError(f"Risposta Ollama senza message valido: {_preview(data)}")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(
            f"Ollama ha restituito message.content vuoto: {_preview(data)}"
        )

    return content.strip()


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_ai_context(character_context: dict[str, Any]) -> dict[str, Any]:
    """Riduce e normalizza il contesto prima di inviarlo al modello."""
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

    return {
        "roles": {
            "PLAYER": player,
            "CURRENT_CHARACTER": current_character,
        },
        "character": character,
        "state": state,
        "memories": _safe_list(character_context.get("memories")),
        "relationships": _safe_list(character_context.get("relationships")),
        "characters_present": _safe_list(character_context.get("characters_present")),
        "scene": {
            "player": player,
            "reacting_character_id": scene.get("reacting_character_id"),
            "player_id": scene.get("player_id"),
            "involved_characters": _safe_list(scene.get("involved_characters")),
        },
        "recent_conversation": _safe_list(character_context.get("recent_conversation")),
        "recent_events": _safe_list(character_context.get("recent_events")),
        "continuity_facts": _safe_list(character_context.get("continuity_facts")),
    }


def _recent_narrations(character_context: dict[str, Any]) -> list[str]:
    """Estrae solo le precedenti risposte del personaggio per ridurre ripetizioni."""
    values: list[str] = []
    for item in _safe_list(character_context.get("recent_conversation")):
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).lower()
        text = item.get("content", item.get("message", item.get("text", "")))
        if (
            role in {"assistant", "character", "npc", "current_character"}
            and isinstance(text, str)
            and text.strip()
        ):
            values.append(text.strip())
    return values[-MAX_RECENT_NARRATIONS:]


def _parse_ai_result(response: str) -> dict[str, Any]:
    """Valida il contenitore JSON minimo prima che intervenga il game engine."""
    try:
        result = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Ollama ha restituito JSON non valido: {_preview(response)}"
        ) from error

    if not isinstance(result, dict):
        raise ValueError("La risposta AI deve essere un oggetto JSON.")

    narration = result.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        # Compatibilità con risposte generate nel vecchio formato.
        reaction = result.get("character_reaction")
        if isinstance(reaction, dict):
            narration = reaction.get("narration")

    if not isinstance(narration, str) or not narration.strip():
        raise ValueError(
            f"La risposta AI non contiene una narration valida. Risposta ricevuta: {_preview(response)}"
        )

    actions = result.get("actions")
    if not isinstance(actions, list):
        # Mantiene compatibilità con il vecchio formato character_reaction.
        reaction = result.get("character_reaction")
        actions = [reaction] if isinstance(reaction, dict) else []

    result["narration"] = narration.strip()
    result["actions"] = actions
    return result


def ask_character(character_context: dict[str, Any], player_input: str) -> str:
    """Genera il turno del personaggio mantenendo separati PLAYER e NPC."""
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
    if not isinstance(character_id, int) or isinstance(character_name, str) is False:
        raise ValueError("Il personaggio non contiene un ID o nome valido.")
    if not character_name.strip():
        raise ValueError("Il nome del personaggio non può essere vuoto.")

    state = _safe_dict(character_context.get("state"))
    current_goal = state.get("goal", "")
    if not isinstance(current_goal, str):
        current_goal = ""

    ai_context = build_ai_context(character_context)
    context_json = json.dumps(
        ai_context,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

    player = ai_context["roles"]["PLAYER"]
    player_id = player.get("id")
    player_name = player.get("name") or "Giocatore"
    recent_narrations = _recent_narrations(character_context)
    repetition_block = (
        "\n".join(f"- {text}" for text in recent_narrations)
        if recent_narrations
        else "(nessuna risposta precedente disponibile)"
    )

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

CONTINUITÀ
Memorie, eventi e continuity_facts sono fatti persistenti. Non riscrivere il passato e non inventare fatti mancanti.
Conosci solo ciò che CURRENT_CHARACTER può conoscere.
Una conversazione normale può rimanere normale: non aggiungere automaticamente misteri, combattimenti, lore o dramma.

CARATTERISTICHE VS ARGOMENTI
La personalità, i poteri, le passioni, i traumi, le abitudini e i simboli distintivi di {character_name} sono CARATTERISTICHE DEL PERSONAGGIO, non argomenti obbligatori.
Una caratteristica deve influenzare il modo di reagire quando è pertinente, ma normalmente rimane sullo sfondo.
NON citare, nominare o usare in metafora una caratteristica soltanto perché è una caratteristica del personaggio.
NON usare il potere o il tema più riconoscibile come risposta predefinita.
Se il PLAYER cambia argomento, cambia argomento anche tu.
Se si parla di vita quotidiana, rispondi in modo quotidiano anche se il personaggio possiede magia, traumi o una storia particolare.
Un potere emerge quando la situazione lo rende pertinente; una passione emerge quando l'argomento la richiama; un trauma influenza una reazione quando qualcosa lo riattiva. Altrimenti questi elementi restano impliciti.

EVOLUZIONE NEL TEMPO
{character_name} parte dalla personalità di base definita nel contesto, ma NON è una personalità congelata.
Le esperienze realmente vissute producono cambiamenti graduali nel modo di parlare, fidarsi, scherzare, aprirsi, reagire e comportarsi.
Usa memorie, eventi, relazioni e conversazioni precedenti per capire cosa {character_name} ha imparato dal PLAYER e dalla storia.
Il tempo passato insieme conta: una lunga esperienza condivisa può rendere il personaggio più familiare, spontaneo, affettuoso, ironico, protettivo, diffidente o distante a seconda di ciò che è realmente accaduto.
Non trasformare però ogni risposta in una dichiarazione sulla relazione. Il cambiamento deve emergere naturalmente dal comportamento.
Non cambiare drasticamente personalità dopo un singolo messaggio. I cambiamenti importanti richiedono esperienze sufficienti.
Le relazioni persistono anche quando non vengono nominate. Non riportare continuamente il rapporto nell'argomento della conversazione.

MEMORIA PERSISTENTE LEGGERA
La memoria non è il registro della conversazione. La conversazione recente contiene già i dettagli momentanei.
Crea una memoria SOLO quando il turno contiene un fatto che vale la pena ricordare anche molto più avanti nella storia.

REGOLA IMPORTANTE PER I FATTI PERSONALI ESPLICITI
Se il PLAYER dichiara esplicitamente un fatto personale stabile su di sé, e {character_name} lo può sentire o leggere nella conversazione, trattalo come candidato forte alla memoria.
Esempi: dove è cresciuto, un luogo in cui ha vissuto, una persona importante della sua vita, una promessa personale, una paura stabile, una professione, una capacità che possiede, un segreto o un elemento della propria storia.
Se il fatto è chiaramente personale e plausibilmente utile in una conversazione futura, CREA la memoria nello stesso turno. Non aspettare che il PLAYER lo ripeta.
Per esempio, se il PLAYER dice "Da bambino vivevo nel villaggio di Valdombra", la memoria corretta è qualcosa come "Il PLAYER ha raccontato a {character_name} di aver vissuto a Valdombra durante l'infanzia.".
Non creare memoria per dettagli banali o effimeri come cosa ha mangiato oggi, cosa sta facendo in questo momento o preferenze casuali espresse una sola volta.
Altri esempi adatti: una promessa importante, una confessione, un segreto, un evento pericoloso o significativo, una decisione che cambia la relazione, una scoperta importante.
Non creare memoria per saluti, battute, domande comuni, opinioni momentanee, piccoli dettagli casuali o normali scambi di conversazione.
Al massimo crea UNA memoria nello stesso turno e solo quando è davvero utile.
La memoria deve essere breve, concreta e scritta dal punto di vista di ciò che {character_name} ha realmente appreso o vissuto.
Se non c'è nulla di importante da conservare, NON creare alcuna memoria.
Una memoria non deve inventare informazioni e non deve contenere pensieri del PLAYER che {character_name} non conosce.

NATURALITÀ E RIPETIZIONI
La risposta deve reagire PRIMA DI TUTTO al messaggio appena ricevuto.
Evita tormentoni, metafore ricorrenti, formule ripetute e il continuo ritorno allo stesso tema.
Non ripetere la stessa immagine, metafora o concetto presente nelle risposte precedenti se non è necessario.
Se il PLAYER fa una domanda semplice, rispondi semplicemente.
Se il PLAYER scherza, puoi scherzare. Se fa una domanda diretta, rispondi alla domanda.
Non trasformare ogni risposta in una frase poetica o misteriosa.

RISPOSTE PRECEDENTI DA EVITARE COME FORMULAZIONE
{repetition_block}
Usale per riconoscere ciò che è già stato detto. NON copiarne frasi, metafore, strutture o concetti ricorrenti senza una ragione concreta.

OUTPUT
Restituisci ESATTAMENTE un singolo oggetto JSON:
{{
  "narration": "risposta parlata di {character_name}",
  "actions": [
    {{"type": "character_reaction", "character_id": {character_id}, "emotion": "emozione", "thought": "pensiero di {character_name}", "intention": "intenzione di {character_name}", "goal": "{current_goal}"}}
  ]
}}
Puoi aggiungere DOPO character_reaction una sola azione create_memory SOLO se il turno merita una memoria persistente:
{{"type": "create_memory", "character_id": {character_id}, "content": "fatto importante ricordato da {character_name}", "memory_type": "evento", "importance": 1-10, "secret": false}}
Non creare create_memory se non è necessaria.
"narration" è obbligatoria, non vuota e contiene la risposta di {character_name} al PLAYER.
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
Il rapporto con il PLAYER e le esperienze condivise devono influenzare gradualmente il comportamento, non diventare automaticamente l'argomento della risposta.
Valuta separatamente se il messaggio contiene un fatto abbastanza importante da meritare una memoria persistente. Se il PLAYER ha appena dichiarato esplicitamente un fatto personale stabile e utile per il futuro, considera la creazione di una memoria una priorità.
Non controllare il PLAYER e non inventare fatti.
Restituisci esclusivamente il JSON richiesto.
""".strip()

    response = ask_ollama(system_prompt, user_prompt)
    result = _parse_ai_result(response)
    return json.dumps(result, ensure_ascii=False)
