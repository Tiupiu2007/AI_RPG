from __future__ import annotations

import json
import re

from app.ai_provider import ask_ollama
from app.game_engine import advance_turn, ensure_game_state, snapshot
from app.database.characters_db import get_character, save_character
from app.memory.memory import create_event, create_memory, get_character_memories, get_recent_events, reset_character_history


MAX_HISTORY = 40
MAX_MEMORIES = 20
MAX_EVENTS = 20
MAX_CANON_FACTS = 100


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
    extra.pop("world_canon", None)
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
        "authoritative_game_state": snapshot(extra),
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
        "world_canon": extra.get("world_canon", []) if isinstance(extra.get("world_canon"), list) else [],
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

IL PERSONAGGIO APPARTIENE AL PLAYER
Il PLAYER controlla anche i fatti personali del proprio personaggio.
Non inventare o aggiungere senza autorizzazione:
- oggetti, equipaggiamento o accessori che il PLAYER non ha già dichiarato o che non risultano nel CONTEXT;
- poteri, magie, abilità o capacità non presenti nel CONTEXT;
- ferite, condizioni fisiche o effetti sul corpo non determinati dal gioco;
- ricordi, esperienze passate, relazioni o conoscenze personali non presenti nel CONTEXT;
- pensieri, emozioni, preferenze o reazioni interiori del PLAYER;
- caratteristiche fisiche o dettagli dell'aspetto non presenti nel CONTEXT.
Se un elemento personale non è specificato, lascialo non determinato oppure chiedi al PLAYER attraverso la situazione, senza inventarlo come fatto.
Il GAME ENGINE e il CONTEXT sono la fonte di verità per inventario, abilità, magie, condizioni e altri dati del PLAYER.

Il messaggio del PLAYER è un'azione/intenzione da interpretare, non un invito a continuare automaticamente le sue azioni.
Se il PLAYER scrive "mi alzo", puoi descrivere il risultato dell'alzarsi, ma non puoi aggiungere "poi esco dalla stanza".
Se il PLAYER scrive "guardo la porta", puoi descrivere ciò che vede, ma non puoi decidere che apre la porta.
Se il PLAYER parla con qualcuno, scrivi la risposta dell'NPC e le conseguenze osservabili, non le parole successive del PLAYER.

CONTINUITÀ E CANONE
La storia deve avere continuità ferrea.
- Il CONTEXT, lo stato autorevole del GAME ENGINE, la cronologia della conversazione e gli eventi già narrati sono la fonte autorevole per ciò che è già stabilito.
- Quando introduci un fatto nella narrazione, quel fatto diventa canonico per i turni successivi. I fatti canonici importanti sono riportati anche in `world_canon` nel CONTEXT.
- Non contraddire, sostituire o riscrivere retroattivamente fatti già stabiliti.
- Puoi aggiungere nuovi dettagli in seguito, ma devono essere compatibili con ciò che hai già detto.
- Non trasformare una nuova versione di un luogo, oggetto o personaggio nella sua versione "vera" se contraddice quanto narrato prima.
- Se un elemento era realmente nascosto, lontano, al buio, coperto o non riconoscibile, puoi farlo scoprire più avanti spiegando implicitamente o esplicitamente perché non era stato notato prima. Non usare questa possibilità per correggere una dimenticanza o una contraddizione.
- Non inventare un passato del PLAYER, relazioni, ricordi o fatti precedenti come se fossero sempre esistiti.
- Non cambiare statistiche, HP, stamina, mana, inventario, relazioni o altre variabili numeriche solo perché lo racconti nella narrazione. Questi valori sono controllati dal GAME ENGINE.

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

SCOPERTE PROGRESSIVE
Non rivelare automaticamente tutto ciò che esiste in una scena appena il PLAYER la guarda.
Distingui tra ciò che è immediatamente percepibile e ciò che richiede un'osservazione, un esame o un'interazione più approfondita.
- Un'azione generica come "guardo la porta" deve descrivere soprattutto ciò che è visibile a colpo d'occhio.
- Un'azione specifica come "esamino la porta", "guardo le incisioni" o "cerco una serratura" può rivelare dettagli più piccoli o nascosti, se plausibili.
- Un'interazione come toccare, aprire, annusare, ascoltare attentamente o usare magia può rivelare ulteriori proprietà o provocare conseguenze.
- Non aggiungere automaticamente misteri, maledizioni, magia, segreti, scritte antiche, simboli enigmatici, messaggi criptici o elementi soprannaturali solo per rendere interessante una scena.
- La maggior parte degli elementi deve essere ordinaria. Una porta può essere semplicemente una porta, una crepa può essere semplicemente una crepa e un soffitto può essere semplicemente un soffitto.
- Non aggiungere una scritta, un'incisione, una runa o un simbolo se non c'è una ragione narrativa concreta per cui debba esistere.
- Non rendere intenzionalmente enigmatici dettagli normali usando formule come "sembra quasi", "come se", "pare che", "quasi a suggerire" o descrizioni ambigue quando non c'è un fatto concreto dietro.
- Gli elementi eccezionali devono avere una ragione narrativa e devono essere relativamente rari.
- Non trasformare ogni osservazione del PLAYER in un indizio, presagio, minaccia o mistero.
- Se il PLAYER guarda una parte dell'ambiente, privilegia ciò che una persona vedrebbe normalmente: forma, materiali, dimensioni apparenti, usura, sporco, luce e oggetti presenti.
- Non fare apparire nuovi dettagli importanti soltanto perché il PLAYER li ha già osservati in un turno precedente senza averli notati. Se un dettaglio era chiaramente visibile e rilevante, trattalo come già percepito.
- Puoi aggiungere dettagli ordinari non ancora descritti quando il PLAYER osserva una zona più da vicino, ma devono essere compatibili con il canone.
- Non è necessario che ogni osservazione introduca un nuovo dettaglio importante: se non c'è nulla di particolare da vedere, una risposta semplice e concreta è corretta.
- Se un dettaglio è nascosto, impercettibile o richiede una condizione particolare, rendi coerente la sua scoperta con ciò che il PLAYER ha fatto.
La curiosità del PLAYER deve guidare il livello di dettaglio della scoperta.

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
Non trasformare automaticamente ogni dettaglio ambientale in memoria o stato del database. Usa `world_canon` solo per fatti persistenti e utili alla continuità, non per ogni frase descrittiva.
Non modificare lo stato autorevole del GAME ENGINE inventando numeri o effetti meccanici nella narrazione.

OUTPUT
Restituisci esclusivamente un singolo JSON valido:
{{
  "narration": "la risposta del Game Master",
  "canon_facts": ["solo i nuovi fatti persistenti importanti che hai stabilito in questo turno"]
}}
`canon_facts` deve contenere frasi brevi, concrete e verificabili. Inserisci solo fatti che dovranno restare veri nei turni futuri (per esempio: "La porta della stanza è di legno scuro", "Fuori dalla finestra si vede una foresta"). Non inserire azioni o pensieri del PLAYER, risultati temporanei o semplici impressioni stilistiche. Se non hai stabilito nuovi fatti persistenti, usa [].

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

    ensure_game_state(extra)
    advance_turn(extra)
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

    canon_facts = result.get("canon_facts", [])
    if not isinstance(canon_facts, list):
        canon_facts = []
    canon_facts = [str(f).strip() for f in canon_facts if isinstance(f, str) and f.strip()]
    canon_facts = canon_facts[:20]

    existing_canon = extra.get("world_canon", [])
    if not isinstance(existing_canon, list):
        existing_canon = []
    existing_canon = [str(f).strip() for f in existing_canon if isinstance(f, str) and f.strip()]
    for fact in canon_facts:
        if fact not in existing_canon:
            existing_canon.append(fact)
    extra["world_canon"] = existing_canon[-MAX_CANON_FACTS:]

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
            "canon_facts": canon_facts,
            "explicit_memory_id": memory_id,
        },
    )

    return {
        "narration": narration,
        "conversation": history,
        "event_id": event_id,
        "created_memory_id": memory_id,
    }
