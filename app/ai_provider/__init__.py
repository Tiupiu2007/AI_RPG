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
    if not isinstance(character_context, dict):
        raise ValueError("character_context deve essere un dizionario.")

    character = character_context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene un personaggio valido.")

    roles = _safe_dict(character_context.get("roles"))
    player = _safe_dict(roles.get("player")) or _safe_dict(roles.get("PLAYER"))
    current_character = roles.get("current_character")
    if not isinstance(current_character, dict):
        current_character = roles.get("CURRENT_CHARACTER")
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
        if not isinstance(character_id, int)
        or not isinstance(item, dict)
        or item.get("character_id") == character_id
    ]
    events = [
        item for item in _safe_list(character_context.get("recent_events"))
        if not isinstance(character_id, int)
        or not isinstance(item, dict)
        or item.get("character_id") == character_id
    ]

    return {
        "context_scope": {
            "character_id": character_id,
            "memory_scope": scope.get("memory_scope", f"ONLY_CHARACTER_{character_id}"),
            "event_scope": scope.get("event_scope", f"ONLY_CHARACTER_{character_id}"),
            "conversation_scope": scope.get("conversation_scope", f"ONLY_CHARACTER_{character_id}"),
        },
        "roles": {"PLAYER": player, "CURRENT_CHARACTER": current_character},
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


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).strip(" .!?\"'“”‘’")


def _is_duplicate(narration: str, previous: list[str]) -> bool:
    normalized = _normalize(narration)
    return bool(normalized) and any(
        normalized == _normalize(item) for item in previous if isinstance(item, str)
    )


_IDENTITY_EVASION_PATTERNS = (
    "il mio passato",
    "un passato senza",
    "un silenzio che non",
    "un vuoto che",
    "non posso dirti",
    "non posso ricordare",
    "non riesco a ricordare",
    "è un mistero",
    "è un enigma",
    "bosco senza sentieri",
    "non si spezza",
)


def _looks_like_generic_identity_evasion(narration: str, player_input: str) -> bool:
    question = _normalize(player_input)
    answer = _normalize(narration)
    if not question or not answer:
        return False

    asks_identity = bool(re.search(
        r"\b(dove|quando|chi|quale|come|qual è)\b.*\b"
        r"(nato|nata|nascita|nome|cognome|infanzia|bambino|bambina|famiglia|genitori|"
        r"vivevi|vivevo|vissuto|vissuta|cresciuto|cresciuta|passato|origine)\b",
        question,
        re.IGNORECASE,
    ))
    return asks_identity and any(pattern in answer for pattern in _IDENTITY_EVASION_PATTERNS)


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


def _reference_hint(player_input: str) -> str:
    """Risoluzione deterministica dei riferimenti in prima persona."""
    text = " ".join(player_input.strip().split()).lower()
    padded = f" {text} "
    markers = (
        " io ", "sono nato", "sono nata", "sono cresciuto", "sono cresciuta",
        "ero ", "avevo ", "ho ", "vivevo ", "abitavo ", "venivo ",
        "mi chiamo", "mio ", "mia ", "miei ", "mie ", "me ", "mi ",
    )
    if not any(marker in padded for marker in markers):
        return player_input

    return (
        f"{player_input}\n\n"
        "[ENGINE — RIFERIMENTO OBBLIGATORIO]\n"
        "Le forme in prima persona del messaggio appartengono al PLAYER. "
        "'Sono nato', 'sono cresciuto', 'vivevo', 'ero', 'avevo', 'mio', 'mia', 'miei', 'mie' "
        "si riferiscono al PLAYER. 'Sai dove sono nato?' significa 'Sai dove è nato il PLAYER?'. "
        "Cerca la risposta nelle informazioni che il PLAYER ha comunicato a questo personaggio. "
        "Non trasferire mai un fatto del PLAYER all'identità del CURRENT_CHARACTER."
    )


def ask_character(character_context: dict[str, Any], player_input: str) -> str:
    if not isinstance(character_context, dict):
        raise ValueError("character_context deve essere un dizionario.")

    original_input = str(player_input or "").strip()
    if not original_input:
        raise ValueError("player_input non può essere vuoto.")

    character = character_context.get("character")
    if not isinstance(character, dict):
        raise ValueError("Il contesto non contiene un personaggio valido.")

    character_id = character.get("id")
    character_name = character.get("name")
    if not isinstance(character_id, int) or isinstance(character_id, bool) or not isinstance(character_name, str) or not character_name.strip():
        raise ValueError("Il personaggio non contiene un ID o nome valido.")

    scope = _safe_dict(character_context.get("context_scope"))
    if scope.get("character_id") != character_id:
        raise ValueError("Il contesto AI non è isolato dal personaggio corrente.")

    ai_context = build_ai_context(character_context)
    context_json = json.dumps(ai_context, indent=2, ensure_ascii=False, default=str)
    player = ai_context["roles"]["PLAYER"]
    player_id = player.get("id")
    player_name = player.get("name") or "Giocatore"
    state = _safe_dict(character_context.get("state"))
    current_goal = state.get("goal", "") if isinstance(state.get("goal", ""), str) else ""
    recent = _recent_narrations(character_context)
    previous = "\n".join(f"- {text}" for text in recent) if recent else "(nessuna)"

    system_prompt = f"""
Sei {character_name}, un personaggio reale di un GDR narrativo persistente.
Interpreti esclusivamente CURRENT_CHARACTER {character_name}, ID {character_id}.
PLAYER è un'entità distinta: ID {player_id}, nome {player_name}.

REGOLE DI CONOSCENZA
Il JSON fornito dal game engine è l'unica fonte autorevole.
Se un fatto non è presente in identità, stato, memorie, eventi, relazioni, conversazione autorizzata o scena, non lo conosci.
Non inventare ricordi per riempire vuoti.
Non trasferire mai informazioni tra PLAYER e CURRENT_CHARACTER.

RISOLUZIONE DEI RIFERIMENTI
Le forme 'io/me/mi/mio/mia/miei/mie/sono/ero/avevo/ho/vivevo' riferite al parlante del messaggio sono del PLAYER.
Le forme 'tu/te/ti/tuo/tua/tuoi/tue/sei/eri/avevi/hai/vivevi' rivolte all'interlocutore sono di CURRENT_CHARACTER.
'Dove sono nato?' = nascita del PLAYER.
'Dove sei nato?' = nascita di CURRENT_CHARACTER.
'Che cosa ti ho raccontato?' = ciò che PLAYER ha comunicato a CURRENT_CHARACTER.
Non confondere mai i due.

MEMORIA E FONTE
Se PLAYER ti ha raccontato un fatto, puoi ricordarlo come informazione ricevuta dal PLAYER.
Non dire 'te l'ho detto' per un fatto che in realtà ti ha detto PLAYER.
Usa 'me l'hai detto', 'me l'avevi raccontato', ecc.
Se il fatto non è noto, dì semplicemente che non lo sai o non lo ricordi.

REGOLA FONDAMENTALE SULL'IDENTITÀ
Una lacuna di memoria è una lacuna di memoria, non una crisi di identità.
Non trasformare domande normali sul passato in risposte poetiche o drammatiche.
Non usare come formule ricorrenti: 'il mio passato è...', 'un bosco senza sentieri', 'un silenzio che non si spezza', 'un vuoto', 'è un mistero', 'non posso dirti'.
Se non ricordi il luogo di nascita, una risposta valida è: 'Non lo so. Non ricordo dove sono nato.'
Le crisi di identità devono apparire soltanto quando sono realmente pertinenti alla situazione, alle memorie, agli eventi o alla psicologia del personaggio.

RUOLO GDR
Rispondi prima al messaggio appena ricevuto.
Una domanda semplice riceve una risposta semplice.
Non rendere ogni scambio poetico, misterioso o drammatico.
Poteri, traumi, passioni e lore influenzano il comportamento solo quando pertinenti.
Il personaggio evolve gradualmente in base alle esperienze reali e alle relazioni.
Non cambiare personalità dopo un singolo messaggio.

ANTI-RIPETIZIONE
Non ripetere le stesse frasi, metafore o strutture delle risposte precedenti.
Risposte precedenti da evitare:
{previous}

MEMORIA PERSISTENTE
Crea una sola create_memory soltanto quando il turno contiene un fatto importante e utile anche molto più avanti.
Un fatto personale stabile dichiarato dal PLAYER può meritare memoria.
Non creare memoria per domande, saluti, battute o dettagli casuali.

OUTPUT JSON OBBLIGATORIO
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
Dopo character_reaction puoi aggiungere al massimo una create_memory se necessaria.
Non controllare mai PLAYER.
Restituisci esclusivamente JSON valido.
""".strip()

    user_prompt = f"""
CONTESTO AUTOREVOLE:
{context_json}

MESSAGGIO ATTUALE DEL PLAYER:
{_reference_hint(original_input)}

Rispondi direttamente al messaggio attuale.
Controlla prima chi è il soggetto e se l'informazione richiesta è realmente conosciuta.
Se non la conosci, dillo chiaramente senza inventare e senza trasformare automaticamente la risposta in una crisi di identità.
Mantieni il comportamento naturale da GDR.
""".strip()

    result = _parse_ai_result(ask_ollama(system_prompt, user_prompt))

    if _is_duplicate(result["narration"], recent) or _looks_like_generic_identity_evasion(result["narration"], original_input):
        retry_prompt = f"""
CONTROLLO DEL GAME ENGINE
La risposta precedente non è accettabile per un GDR perché è ripetitiva o evasiva.
Messaggio del PLAYER:
{original_input}

Genera una nuova risposta.
- Rispondi direttamente alla domanda.
- Se il fatto manca dal contesto, dì semplicemente che non lo sai/non lo ricordi.
- Non usare metafore su boschi, silenzi, vuoti, misteri o passato.
- Non inventare dettagli.
- Non attribuire al CURRENT_CHARACTER un fatto del PLAYER.
- Mantieni la personalità, ma sii concreto.
- Una o due frasi sono sufficienti se bastano.

Restituisci esclusivamente lo stesso JSON richiesto.
""".strip()
        retry = _parse_ai_result(ask_ollama(system_prompt, f"{user_prompt}\n\n{retry_prompt}"))
        if not _is_duplicate(retry["narration"], recent) and not _looks_like_generic_identity_evasion(retry["narration"], original_input):
            result = retry

    return json.dumps(result, ensure_ascii=False)
