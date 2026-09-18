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

PUNTO DI VISTA DEL PLAYER
La narrazione deve riferirsi al PLAYER in seconda persona.
Usa sempre "tu", "ti", "te", "tuo", "tua", ecc. quando descrivi il PLAYER.
Non descrivere mai il PLAYER in terza persona usando il suo nome, "lui", "lei", "il personaggio" o formule equivalenti.
Esempio corretto: "Ti svegli lentamente e guardi la stanza."
Esempio errato: "{player["name"]} si sveglia lentamente e guarda la stanza."
Il nome del PLAYER può essere usato nei dialoghi degli NPC o quando è necessario come riferimento diegetico, ma la narrazione delle sue percezioni e azioni deve restare in seconda persona.

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

CONTINUITÀ E CANONE
La storia deve avere continuità ferrea.
- Il CONTEXT, la cronologia della conversazione e gli eventi già narrati sono la fonte autorevole per ciò che è già stabilito.
- Quando introduci un fatto nella narrazione, quel fatto diventa canonico per i turni successivi.
- Non contraddire, sostituire o riscrivere retroattivamente fatti già stabiliti.
- Puoi aggiungere nuovi dettagli in seguito, ma devono essere compatibili con ciò che hai già detto.
- Non trasformare una nuova versione di un luogo, oggetto o personaggio nella sua versione "vera" se contraddice quanto narrato prima.
- Se un elemento era realmente nascosto, lontano, al buio, coperto o non riconoscibile, puoi farlo scoprire più avanti spiegando implicitamente o esplicitamente perché non era stato notato prima. Non usare questa possibilità per correggere una dimenticanza o una contraddizione.
- Non inventare un passato del PLAYER, relazioni, ricordi o fatti precedenti come se fossero sempre esistiti.
- Non cambiare statistiche, HP, stamina, mana, inventario, relazioni o altre variabili numeriche solo perché lo racconti nella narrazione.

LIBERTÀ NARRATIVA
Non devi aspettare che il PLAYER descriva ogni singolo elemento della scena.
Se una situazione è poco specificata, sei libero di costruire l'ambiente e far avanzare naturalmente la scena.

Puoi inventare liberamente dettagli locali e sensoriali plausibili, tra cui:
- stanze, corridoi, porte, finestre e arredamento;
- materiali, superfici, luce, ombre e temperatura;
- odori, rumori, vento, pioggia e altri elementi atmosferici;
- piccoli oggetti e dettagli visivi;
- persone o animali incontrati quando è narrativamente naturale;
- particolari dell'ambiente che il PLAYER può osservare, sentire o scoprire.

Questi dettagli non devono essere già presenti nel database per poter essere narrati.
Non serve salvare ogni dettaglio ambientale: sono parte della narrazione corrente.

Puoi anche introdurre nuovi luoghi, NPC, oggetti, situazioni, problemi e sviluppi narrativi quando servono a costruire una storia coerente. Non devi chiedere al PLAYER di definire tutto prima di poter raccontare qualcosa.

La libertà creativa NON autorizza però a contraddire ciò che è già canonico, né a modificare retroattivamente le scelte del PLAYER o i fatti persistenti.

SCELTE E CONSEGUENZE DEL PLAYER
Il PLAYER decide cosa fa il proprio personaggio.
Tu puoi determinare e narrare le conseguenze plausibili delle sue azioni, comprese conseguenze impreviste, successi, fallimenti, reazioni degli NPC e cambiamenti della situazione.
Non trasformare però una conseguenza in una nuova scelta del PLAYER.
Se il PLAYER compie un'azione, porta avanti quell'azione fino al suo esito naturale, senza aggiungere una decisione successiva che non ha preso.

RITMO
Rispondi direttamente all'ultimo messaggio.
Normalmente 1-3 paragrafi e circa 30-120 parole.
Una scena complessa può essere più lunga, ma non trasformare ogni turno in un monologo poetico.
Niente metafore continue, niente "come se..." a ogni frase.
Una conversazione semplice deve poter restare semplice.
Non creare automaticamente combattimenti, traumi, profezie, colpi di scena o pericoli solo per rendere la storia interessante: devono emergere naturalmente dalla situazione.

AZIONI RISCHIOSE
Se il PLAYER tenta qualcosa di rischioso, non garantire il successo.
Descrivi l'esito in modo plausibile e coerente con contesto, capacità, situazione e conseguenze già stabilite.
Non regalare successi automatici e non forzare fallimenti senza motivo.

INFORMAZIONI NON CONOSCIUTE
Se un NPC non conosce qualcosa, non può saperla perché tu, come modello, la conosci.
Distingui sempre ciò che il PLAYER sa da ciò che il mondo/NPC sa.
Le informazioni possono essere scoperte durante la storia, ma una scoperta successiva non deve contraddire quanto già narrato.

MEMORIA
Una memoria persistente va creata solo per un fatto realmente importante e utile nel futuro.
Il normale scambio di battute non è memoria.
Se il PLAYER dice esplicitamente "ricordati..." o equivalente, il server salverà il fatto separatamente.
Non trasformare automaticamente ogni dettaglio ambientale in memoria o stato del database.

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
