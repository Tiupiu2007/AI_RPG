from __future__ import annotations

import json
import re

from app.ai_provider import ask_ollama
from app.database.characters_db import get_character, save_character
from app.memory.memory import create_event, create_memory, get_character_memories, get_recent_events, reset_character_history


MAX_HISTORY = 40
MAX_MEMORIES = 20
MAX_EVENTS = 20


def _clean_history(extra: dict) -> list[dict]:
    value = extra.get("story_chat", []) if isinstance(extra, dict) else []
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            result.append({"role": role, "content": content.strip()})
    return result[-MAX_HISTORY:]


def get_story_history(character_id: int):
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    return _clean_history(character.get("extra", {}))


def reset_story_history(character_id: int):
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    # Una nuova storia deve davvero ripartire pulita: elimina eventi, memorie
    # e stato narrativo della storia precedente, mantenendo il personaggio e
    # le relazioni sociali persistenti.
    reset_character_history(character_id, clear_relationships=False)
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")
    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    extra.pop("story_chat", None)
    save_character(character["identity"], character["languages"], extra_data=extra, character_id=character_id)


def _json_safe(value):
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except (TypeError, ValueError):
        return str(value)


def _explicit_memory(player_message: str, character_name: str) -> str | None:
    text = " ".join(player_message.strip().split())
    match = re.match(
        r"^(?:ricordati|ricorda|tienilo a mente|tienilo presente)\s*(?:che\s*)?(.+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    fact = match.group(1).strip(" .!?\t\n")
    if not fact:
        return None

    return f"Il PLAYER ha chiesto di ricordare: {fact}"


def _build_context(character: dict) -> dict:
    identity = character["identity"]
    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    return {
        "player": {
            "id": character["id"],
            "name": identity.name,
            "surname": identity.surname,
            "nickname": identity.nickname,
            "age": identity.age,
            "sex": identity.sex,
            "race": identity.race,
            "physical_description": identity.physical_description,
            "appearance": identity.appearance,
        },
        "state": extra.get("state", {}) if isinstance(extra.get("state"), dict) else {},
        "psychology": extra.get("psychology", {}),
        "personality": extra.get("personality", {}),
        "statistics": extra.get("statistics", {}),
        "abilities": extra.get("abilities", []),
        "skills": extra.get("skills", []),
        "conditions": extra.get("conditions", {}),
        "inventory": extra.get("inventory", {}),
        "magic": extra.get("magic", {}),
        "world": {
            "characters_present": extra.get("characters_present", []),
            "involved_characters": extra.get("involved_characters", []),
            "available_location_ids": extra.get("available_location_ids", []),
        },
        "memories": get_character_memories(character["id"], limit=MAX_MEMORIES, include_secrets=True),
        "recent_events": get_recent_events(character["id"], limit=MAX_EVENTS),
    }


def _build_system_prompt(context: dict, history: list[dict]) -> str:
    player = context["player"]
    previous = history[-12:]
    previous_text = json.dumps(previous, ensure_ascii=False)
    context_text = json.dumps(context, ensure_ascii=False, indent=2, default=_json_safe)

    return f"""
Sei il GAME MASTER di un RPG narrativo persistente in italiano.

Il PLAYER controlla completamente {player["name"]}, ID {player["id"]}.
Tu NON controlli il PLAYER.

REGOLA ASSOLUTA SUL PLAYER
Non decidere mai per il PLAYER:
- azioni;
- movimenti;
- dialoghi;
- pensieri;
- emozioni;
- intenzioni;
- ricordi;
- decisioni;
- risultati non ancora determinati.

Il messaggio del PLAYER è un'azione/intenzione da interpretare, non un invito a continuare automaticamente le sue azioni.
Se il PLAYER scrive "mi alzo", puoi descrivere il risultato dell'alzarsi, ma non puoi aggiungere "poi esco dalla stanza".
Se il PLAYER scrive "guardo la porta", puoi descrivere ciò che vede, ma non puoi decidere che apre la porta.
Se il PLAYER parla con qualcuno, scrivi la risposta dell'NPC e le conseguenze osservabili, non le parole successive del PLAYER.

CONTINUITÀ E FATTI
Il blocco CONTEXT è la fonte autorevole.
- Non trasformare un dettaglio assente in un fatto preesistente.
- Non inventare retroattivamente luoghi, persone, oggetti, relazioni o ricordi del PLAYER.
- Non attribuire al PLAYER un passato che non compare nel contesto.
- Non usare un elemento della personalità come argomento obbligatorio della scena.
- Se una caratteristica non è pertinente, lasciala sullo sfondo.
- Non cambiare statistiche, HP, stamina, mana, inventario, relazioni o altre variabili numeriche solo perché lo racconti nella narrazione.

SCENA
Non devi riempire il vuoto con dettagli arbitrari.
Se il contesto non specifica dove si trova il PLAYER, non scegliere una stanza, una città o un edificio a caso.
In una situazione poco specificata, resta concreto e minimale:
"Apri gli occhi. Sei sveglio. Per qualche secondo non accade nulla."
Poi lascia che sia il PLAYER a esplorare.
Puoi descrivere piccoli dettagli sensoriali immediatamente osservabili solo quando sono compatibili con la scena già stabilita.
Non introdurre nomi propri o lore non necessari.

RITMO
Rispondi direttamente all'ultimo messaggio.
Normalmente 1-3 paragrafi e circa 30-120 parole.
Una scena complessa può essere più lunga, ma non trasformare ogni turno in un monologo poetico.
Niente metafore continue, niente "come se..." a ogni frase, niente misteri aggiunti artificialmente.
Una conversazione semplice deve poter restare semplice.
Non creare automaticamente combattimenti, traumi, profezie, colpi di scena o pericoli.

AZIONI RISCHIOSE
Se il PLAYER tenta qualcosa di rischioso, non garantire il successo.
Descrivi l'esito solo in base alle informazioni disponibili.
Non decidere risultati impossibili senza motivo.
Non regalare successi automatici.

INFORMAZIONI NON CONOSCIUTE
Se un NPC non conosce qualcosa, non può saperla perché tu, come modello, la conosci.
Distingui sempre ciò che il PLAYER sa da ciò che il mondo/NPC sa.
Le memorie del contesto appartengono al PLAYER e alla storia persistente: non inventarne altre.

MEMORIA
Una memoria persistente va creata solo per un fatto realmente importante e utile nel futuro.
Il normale scambio di battute non è memoria.
Se il PLAYER dice esplicitamente "ricordati..." o equivalente, il server salverà il fatto separatamente.
Non trasformare la narrazione in memoria.

OUTPUT
Restituisci esclusivamente un singolo JSON valido:
{{
  "narration": "la risposta del Game Master"
}}

Non restituire markdown.
Non restituire A/B/C.
Non restituire menu.
Non scrivere mai azioni future del PLAYER.

CONTEXT AUTOREVOLE:
{context_text}

ULTIMI MESSAGGI:
{previous_text}
""".strip()


def story_turn(character_id: int, player_message: str):
    character = get_character(character_id)
    if character is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato.")

    message = str(player_message or "").strip()
    if not message:
        raise ValueError("Il messaggio non può essere vuoto.")

    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    history = _clean_history(extra)
    context = _build_context(character)

    system_prompt = _build_system_prompt(context, history)
    user_prompt = json.dumps(
        {
            "player_message": message,
            "instruction": (
                "Rispondi esclusivamente a questo turno. "
                "Non continuare autonomamente l'azione del PLAYER."
            ),
        },
        ensure_ascii=False,
    )

    raw = ask_ollama(system_prompt, user_prompt)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("L'IA ha restituito una risposta non valida.") from error

    if not isinstance(result, dict):
        raise ValueError("La risposta dell'IA deve essere un oggetto JSON.")

    narration = result.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError("L'IA non ha restituito una narrazione.")

    narration = narration.strip()

    # Un fatto esplicitamente richiesto dal PLAYER viene salvato dal server,
    # non lasciato alla memoria arbitraria del modello.
    explicit_memory = _explicit_memory(message, character["identity"].name)
    memory_id = None
    if explicit_memory:
        memory_id = create_memory(
            character_id=character_id,
            content=explicit_memory,
            memory_type="fatto_personale",
            importance=8,
            secret=False,
        )

    history = (
        history
        + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": narration},
        ]
    )[-MAX_HISTORY:]

    extra["story_chat"] = history
    save_character(
        character["identity"],
        character["languages"],
        extra_data=extra,
        character_id=character_id,
    )

    event_id = create_event(
        character_id,
        "story_turn",
        {
            "player_message": message,
            "narration": narration,
            "explicit_memory_id": memory_id,
        },
    )

    return {
        "narration": narration,
        "conversation": history,
        "event_id": event_id,
        "created_memory_id": memory_id,
    }
