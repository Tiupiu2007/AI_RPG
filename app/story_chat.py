from __future__ import annotations

import json
import re

from app.ai_provider import ask_ollama
from app.game_engine import advance_turn, ensure_game_state, snapshot, execute_action
from app.database.characters_db import get_character, save_character
from app.relationships.relationships import get_character_relationships
from app.world.runtime import advance_world, get_world_context, record_world_event
from app.memory.memory import (
    create_event,
    create_memory,
    create_memory_from_fact,
    get_character_memories,
    get_recent_events,
    get_relevant_memories,
    reset_character_history,
)


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
    extra.pop("world_id", None)
    extra.pop("combat_state", None)
    extra.pop("game_state", None)
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


def _present_characters(extra: dict, player_id: int) -> list[dict]:
    raw = extra.get("characters_present", [])
    if not isinstance(raw, list):
        raw = []
    result = []
    seen = set()
    for item in raw:
        candidate = item.get("id", item.get("character_id")) if isinstance(item, dict) else item
        if not isinstance(candidate, int) or isinstance(candidate, bool) or candidate == player_id or candidate in seen:
            continue
        npc = get_character(candidate)
        if npc is None:
            continue
        seen.add(candidate)
        identity = npc["identity"]
        npc_extra = npc.get("extra", {}) if isinstance(npc.get("extra", {}), dict) else {}
        result.append({
            "id": candidate,
            "name": identity.name,
            "surname": identity.surname,
            "nickname": identity.nickname,
            "age": identity.age,
            "sex": identity.sex,
            "race": identity.race,
            "physical_description": identity.physical_description,
            "appearance": identity.appearance,
            "personality": npc_extra.get("personality", {}),
            "state": npc_extra.get("state", {}),
        })
    return result


def _build_context(character: dict, query: str = "") -> dict:
    identity = character["identity"]
    extra = character.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    world = get_world_context(extra)
    present_characters = _present_characters(extra, character["id"])

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
            **world,
            "characters_present": present_characters,
            "involved_characters": extra.get("involved_characters", []),
            "available_location_ids": extra.get("available_location_ids", []),
            "current_location": extra.get("game_state", {}).get("location"),
        },
        "relationships": get_character_relationships(character["id"]),
        "memories": get_relevant_memories(
            character["id"],
            query,
            limit=MAX_MEMORIES,
            include_secrets=True,
        ) if query.strip() else get_character_memories(character["id"], limit=MAX_MEMORIES, include_secrets=True),
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
Il CONTEXT contiene una selezione di memorie pertinenti all'ultimo messaggio, non necessariamente le più recenti.
Usa quelle memorie per mantenere continuità quando un argomento, una persona, un luogo o un evento ritorna dopo molti turni.
Non presumere che una memoria non presente nella selezione sia falsa: semplicemente non è stata recuperata per questo turno.
Una memoria persistente va creata solo per un fatto realmente importante e utile nel futuro.
Il normale scambio di battute non è memoria.
Se il PLAYER dice esplicitamente "ricordati..." o equivalente, il server salverà il fatto separatamente.
Non trasformare automaticamente ogni dettaglio ambientale in memoria o stato del database. Usa `world_canon` solo per fatti persistenti e utili alla continuità, non per ogni frase descrittiva.
Non modificare lo stato autorevole del GAME ENGINE inventando numeri o effetti meccanici nella narrazione.

OUTPUT
Restituisci esclusivamente un singolo JSON valido:
{{
  "narration": "la risposta del Game Master",
  "action": {{
    "type": "none",
    "target_id": null,
    "target_text": null,
    "parameters": {{}}
  }},
  "canon_facts": ["solo i nuovi fatti persistenti importanti che hai stabilito in questo turno"]
}}
`action` rappresenta esclusivamente l'intento meccanico riconoscibile dal messaggio del PLAYER. Usa `none` quando il turno è puramente narrativo, osservativo o dialogico. Tipi ammessi: `none`, `move`, `inspect`, `interact`, `use_item`, `cast_magic`, `attack`, `defend`, `talk`, `flee`. Per `move`, `target_id` è la destinazione. Per `use_item`, `target_id` o `target_text` identifica l'oggetto. Per `attack`, `target_id` è il personaggio bersaglio. Per `cast_magic` in combattimento, `target_id` è il bersaglio e `parameters.ability_id` identifica la magia/abilità. Non inventare ID: usa solo ID presenti nel CONTEXT. `parameters` deve essere un oggetto semplice. Questa struttura è solo un'interpretazione dell'intento: NON significa che l'azione sia già stata eseguita dal GAME ENGINE.
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


def _parse_action(value) -> dict:
    if not isinstance(value, dict):
        value = {}
    action_type = value.get("type", "none")
    allowed = {
        "none", "move", "inspect", "interact", "use_item",
        "cast_magic", "attack", "defend", "talk", "flee",
    }
    if action_type not in allowed:
        action_type = "none"
    target_id = value.get("target_id")
    if target_id is not None and not isinstance(target_id, (int, str)):
        target_id = None
    target_text = value.get("target_text")
    if target_text is not None and not isinstance(target_text, str):
        target_text = str(target_text)
    parameters = value.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {}
    return {
        "type": action_type,
        "target_id": target_id,
        "target_text": target_text,
        "parameters": parameters,
    }


def _parse_canon_facts(value) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, str) and item.strip():
            fact = " ".join(item.strip().split())
            if len(fact) <= 300 and fact not in result:
                result.append(fact)
    return result[:20]


def _narration_prompt(
    context: dict,
    history: list[dict],
    message: str,
    action: dict,
    engine_result: dict,
) -> str:
    context_text = json.dumps(context, ensure_ascii=False, indent=2, default=_json_safe)
    history_text = json.dumps(history[-12:], ensure_ascii=False)
    action_text = json.dumps(action, ensure_ascii=False)
    result_text = json.dumps(engine_result, ensure_ascii=False, indent=2, default=_json_safe)

    return f"""
Sei il narratore di un RPG persistente. Devi raccontare ESCLUSIVAMENTE il risultato
dell'ultimo turno del PLAYER.

PLAYER:
{message}

INTENTO INTERPRETATO:
{action_text}

RISULTATO AUTOREVOLE DEL GAME ENGINE:
{result_text}

REGOLE OBBLIGATORIE:
- Il PLAYER controlla completamente il proprio personaggio.
- Usa sempre la seconda persona per il PLAYER.
- Non inventare pensieri, emozioni, ricordi, intenzioni, equipaggiamento, condizioni
  fisiche o caratteristiche del PLAYER.
- Non aggiungere una seconda azione del PLAYER dopo quella richiesta.
- Se il GAME ENGINE ha rifiutato l'azione, NON narrarla come riuscita.
- Se il GAME ENGINE ha prodotto conseguenze meccaniche, narrale senza cambiare numeri,
  danni, costi o risultati.
- Gli NPC possono parlare, reagire, muoversi e avere emozioni coerenti con la loro
  personalità, conoscenza e relazione con il PLAYER.
- Un NPC non può sapere fatti che non conosce.
- Usa le memorie pertinenti, gli eventi e le relazioni presenti nel CONTEXT.
- Il mondo può contenere dettagli ordinari inventati sul momento, ma non contraddire
  fatti canonici già stabiliti.
- Non trasformare ogni cosa in mistero, presagio, magia o minaccia.
- Non introdurre dettagli personali del PLAYER solo per rendere la scena più ricca.
- Se il turno è semplice, rispondi semplicemente. Non allungare artificialmente la scena.
- Mantieni coerenza con la cronologia recente.
- Se l'azione è osservativa, descrivi ciò che è plausibilmente percepibile senza
  aggiungere retroattivamente dettagli importanti che prima erano chiaramente visibili.
- I fatti canonici devono essere concreti e riguardare soprattutto il mondo, NPC,
  oggetti o conseguenze persistenti. Non trasformare pensieri o azioni del PLAYER
  in canon.

CONTEXT:
{context_text}

CRONOLOGIA RECENTE:
{history_text}

Restituisci esclusivamente:
{{
  "narration": "testo naturale del narratore",
  "canon_facts": []
}}

La narrazione deve essere in italiano, naturale, concreta e coerente.
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
    world_tick = advance_world(extra, 1)
    history = _clean_history(extra)

    # PASSO 1: l'AI interpreta l'intento. In questa fase non produciamo ancora
    # la narrazione mostrata al giocatore.
    context = _build_context(character, message)
    intent_prompt = _build_system_prompt(context, history)
    raw_intent = ask_ollama(
        intent_prompt,
        json.dumps(
            {
                "player_message": message,
                "instruction": (
                    "INTERPRETAZIONE INTERNA. Non produrre una narrazione definitiva. "
                    "Identifica solamente l'intento meccanico del PLAYER e restituisci "
                    "il JSON previsto. La chiave narration può essere vuota o minimale: "
                    "non verrà mostrata al PLAYER."
                ),
                "output_focus": "action",
            },
            ensure_ascii=False,
        ),
    )

    try:
        parsed_intent = json.loads(raw_intent)
    except json.JSONDecodeError as error:
        raise ValueError("L'IA non ha restituito un JSON valido per l'interpretazione dell'azione.") from error

    if not isinstance(parsed_intent, dict):
        raise ValueError("L'interpretazione dell'azione deve essere un oggetto JSON.")

    action = _parse_action(parsed_intent.get("action"))

    # PASSO 2: il Game Engine decide cosa è realmente successo.
    engine_result = execute_action(extra, action, actor_id=character_id)
    engine_result["world_time"] = world_tick

    if engine_result.get("valid", False):
        action = engine_result.get("action", action)
    else:
        action = engine_result.get("action", action)

    # Salviamo subito lo stato meccanico prima della generazione narrativa.
    save_character(
        character["identity"],
        character["languages"],
        extra_data=extra,
        character_id=character_id,
    )

    # PASSO 3: aggiorniamo il contesto con lo stato reale e chiediamo all'AI
    # solamente di raccontare ciò che il motore ha deciso.
    refreshed = get_character(character_id)
    if refreshed is None:
        raise ValueError(f"Personaggio con ID {character_id} non trovato dopo l'esecuzione.")
    context = _build_context(refreshed, message)

    narration_raw = ask_ollama(
        _narration_prompt(context, history, message, action, engine_result),
        json.dumps(
            {
                "player_message": message,
                "action": action,
                "engine_result": engine_result,
                "instruction": "Racconta ora il risultato già determinato dal Game Engine.",
            },
            ensure_ascii=False,
        ),
    )

    try:
        narration_result = json.loads(narration_raw)
    except json.JSONDecodeError as error:
        raise ValueError("L'IA non ha restituito un JSON valido per la narrazione.") from error

    if not isinstance(narration_result, dict):
        raise ValueError("La narrazione AI deve essere un oggetto JSON.")

    narration = narration_result.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        raise ValueError("L'IA non ha restituito una narrazione valida.")
    narration = narration.strip()

    canon_facts = _parse_canon_facts(narration_result.get("canon_facts"))

    existing_canon = extra.get("world_canon", [])
    if not isinstance(existing_canon, list):
        existing_canon = []
    existing_canon = [
        str(f).strip()
        for f in existing_canon
        if isinstance(f, str) and f.strip()
    ]
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

    world_event_id = record_world_event(
        extra,
        "story_turn",
        {
            "character_id": character_id,
            "player_message": message,
            "action": action,
            "engine_result": engine_result,
        },
    )

    event_id = create_event(
        character_id,
        "story_turn",
        {
            "player_message": message,
            "narration": narration,
            "action": action,
            "engine_result": engine_result,
            "canon_facts": canon_facts,
            "explicit_memory_id": memory_id,
            "world_event_id": world_event_id,
        },
    )

    canon_memory_ids = []
    for fact in canon_facts:
        canon_memory_ids.append(
            create_memory_from_fact(
                character_id=character_id,
                content=fact,
                memory_type="world_fact",
                importance=7,
                source_event_id=event_id,
            )
        )

    save_character(
        character["identity"],
        character["languages"],
        extra_data=extra,
        character_id=character_id,
    )

    return {
        "narration": narration,
        "conversation": history,
        "event_id": event_id,
        "created_memory_id": memory_id,
        "canon_memory_ids": canon_memory_ids,
        "action": action,
        "engine_result": engine_result,
    }
