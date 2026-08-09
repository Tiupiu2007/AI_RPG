import json

from _Robe_Varie.Roba_Vecchia.app.ai_provider import ask_ollama

from _Robe_Varie.Roba_Vecchia.app.characters.character import create_character

from _Robe_Varie.Roba_Vecchia.app.characters.character_stats import (
    create_character_statistics,
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_progression import (
    create_character_progression,
    calculate_xp_required,
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_traits import (
    create_character_trait,
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_psychology import (
    create_character_psychology,
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_classes import (
    find_class,
    create_class,
    add_character_class,
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_memories import (
    create_memory,
)


# =========================================================
# PROGRESS BAR
# =========================================================

def show_progress(percent, message):
    """
    Mostra una barra di avanzamento sulla stessa riga.
    """

    percent = max(
        0,
        min(100, int(percent))
    )

    bar_length = 30

    filled = int(
        bar_length * percent / 100
    )

    bar = (
        "█" * filled
        + "░" * (bar_length - filled)
    )

    print(
        f"\r{message:<35} "
        f"[{bar}] {percent:3d}%",
        end="",
        flush=True
    )


# =========================================================
# TIPI DI MEMORIA
# =========================================================

VALID_MEMORY_TYPES = {
    "experience",
    "event",
    "relationship",
    "discovery",
    "training",
    "trauma",
    "achievement",
    "loss",
    "secret",
}


# =========================================================
# NORMALIZZAZIONE MEMORY TYPE
# =========================================================

def normalize_memory_type(memory_type):
    """
    Converte eventuali tipi di memoria non supportati
    in un tipo sicuro.
    """

    if not isinstance(memory_type, str):
        return "experience"

    memory_type = memory_type.strip().lower()

    aliases = {
        "memory": "experience",
        "past": "experience",
        "life": "experience",
        "story": "experience",
        "incident": "event",
        "occurrence": "event",
        "family": "relationship",
        "relation": "relationship",
        "romance": "relationship",
        "love": "relationship",
        "learning": "training",
        "skill": "training",
        "lesson": "training",
        "traumatic": "trauma",
        "death": "loss",
        "dead": "loss",
        "success": "achievement",
        "found": "discovery",
        "secret_memory": "secret",
    }

    if memory_type in aliases:
        return aliases[memory_type]

    if memory_type in VALID_MEMORY_TYPES:
        return memory_type

    return "experience"


# =========================================================
# PROMPT DI SISTEMA
# =========================================================

SYSTEM_PROMPT = """
Sei un generatore di personaggi per un RPG narrativo
persistente.

Devi generare un personaggio completamente autonomo.

Il personaggio deve essere coerente internamente.

Ogni elemento deve avere un motivo per esistere:

- identità;
- descrizione;
- statistiche;
- progressione;
- tratti;
- psicologia;
- classe;
- memorie;
- famiglia.

Le statistiche devono riflettere fisicamente e mentalmente
il personaggio.

I tratti devono essere coerenti con personalità,
esperienze e comportamento.

La psicologia deve essere coerente con tratti e memorie.

La classe deve essere coerente con statistiche,
personalità, esperienza e storia.

Le memorie devono spiegare alcuni tratti,
paure, desideri, valori o convinzioni.

Il personaggio NON deve essere necessariamente eroico.

Può avere:

- difetti;
- paure;
- insicurezze;
- cattive abitudini;
- contraddizioni interne;
- esperienze negative;
- relazioni complicate.

NON creare un personaggio generico.

NON creare elementi casuali senza collegamento.

Devi produrre ESCLUSIVAMENTE JSON valido.

NON usare Markdown.

NON usare blocchi di codice.

NON aggiungere testo prima o dopo il JSON.


=========================================================
TRAITS
=========================================================

traits.category può essere SOLO:

- personality
- behavior
- physical
- social
- mental
- combat
- racial
- custom

traits.stability può essere SOLO:

- fundamental
- strong
- flexible
- temporary

traits.origin può essere SOLO:

- initial
- experience
- event
- relationship
- training
- acquired
- unknown


=========================================================
PSYCHOLOGY
=========================================================

psychology.type può essere SOLO:

- fear
- desire
- value
- belief
- trauma
- motivation
- insecurity
- attachment
- aversion
- ideal

psychology.stability può essere SOLO:

- fundamental
- strong
- flexible
- temporary

psychology.origin può essere SOLO:

- initial
- experience
- event
- relationship
- training
- acquired
- unknown

NON scambiare MAI questi campi.

"trauma" è valido SOLO in:

psychology.type

"fear" è valido SOLO in:

psychology.type

"personality" è valido SOLO in:

traits.category

"experience" può essere usato in:

traits.origin
psychology.origin


=========================================================
MEMORIE
=========================================================

memory_type deve essere SOLO uno dei seguenti:

- experience
- event
- relationship
- discovery
- training
- trauma
- achievement
- loss
- secret

NON usare altri valori per memory_type.


=========================================================
ESEMPIO TRAIT CORRETTO
=========================================================

{
    "name": "Cauto",
    "description": "Evita di agire senza prima valutare la situazione.",
    "category": "behavior",
    "strength": 78,
    "stability": "strong",
    "origin": "experience",
    "reason": "Un errore commesso in passato gli ha insegnato a essere prudente."
}

NON:

{
    "name": "Cauto",
    "category": "fear",
    "origin": "trauma"
}
""".strip()


# =========================================================
# PROMPT GENERAZIONE
# =========================================================

USER_PROMPT = """
Genera un personaggio completamente casuale per un RPG
fantasy narrativo.

Può appartenere a qualsiasi razza, cultura, classe sociale,
professione o situazione.

Può essere buono, cattivo, neutrale o ambiguo.

Può essere giovane, adulto o anziano.

Non cercare di renderlo speciale per forza.

La priorità assoluta è:

COERENZA INTERNA.

Il personaggio deve sembrare una persona realmente esistita.

La sua storia deve spiegare almeno alcuni dei suoi tratti,
delle sue paure, dei suoi desideri e dei suoi valori.

Le statistiche devono avere senso rispetto alla sua storia.

La classe deve avere senso rispetto alle sue capacità.

Le memorie devono essere compatibili con la sua psicologia.

La famiglia deve essere plausibile.


=========================================================
STRUTTURA OBBLIGATORIA
=========================================================

{
    "character": {
        "name": "string",
        "description": "string"
    },

    "statistics": {
        "strength": 0,
        "constitution": 0,
        "speed": 0,
        "intelligence": 0,
        "perception": 0,
        "willpower": 0,
        "luck": 0
    },

    "progression": {
        "level": 1,
        "xp": 0
    },

    "traits": [
        {
            "name": "string",
            "description": "string",
            "category": "personality",
            "strength": 0,
            "stability": "flexible",
            "origin": "initial",
            "reason": "string"
        }
    ],

    "psychology": [
        {
            "type": "fear",
            "name": "string",
            "description": "string",
            "strength": 0,
            "stability": "flexible",
            "origin": "initial",
            "reason": "string"
        }
    ],

    "class": {
        "name": "string",
        "description": "string",
        "category": "general",
        "level": 1,
        "experience": 0,
        "is_primary": true
    },

    "memories": [
        {
            "content": "string",
            "memory_type": "experience",
            "importance": 1,
            "is_secret": false
        }
    ],

    "family": [
        {
            "character_name": "string",
            "relationship_type": "parent",
            "biological": true,
            "confirmed": true
        }
    ]
}


=========================================================
STATISTICHE
=========================================================

Tutte le statistiche devono essere interi da 1 a 999.

Devono essere coerenti con il personaggio.


=========================================================
PROGRESSIONE
=========================================================

level:

intero da 1 a 999.

xp:

intero >= 0.

Non creare livelli assurdi senza motivo.


=========================================================
TRATTI
=========================================================

Crea da 4 a 7 tratti.

category deve essere una di:

personality
behavior
physical
social
mental
combat
racial
custom

stability deve essere una di:

fundamental
strong
flexible
temporary

origin deve essere una di:

initial
experience
event
relationship
training
acquired
unknown

strength deve essere un intero da 0 a 100.


=========================================================
PSICOLOGIA
=========================================================

Crea da 6 a 10 elementi.

type deve essere una di:

fear
desire
value
belief
trauma
motivation
insecurity
attachment
aversion
ideal

stability:

fundamental
strong
flexible
temporary

origin:

initial
experience
event
relationship
training
acquired
unknown

strength deve essere un intero da 0 a 100.

La psicologia deve essere coerente con il personaggio.


=========================================================
CLASSE
=========================================================

Crea una classe coerente con il personaggio.

La classe può essere completamente originale.

Non limitarti alle classi fantasy tradizionali.


=========================================================
MEMORIE
=========================================================

Crea almeno 5 memorie.

Le memorie devono essere eventi realmente avvenuti
nella vita del personaggio.

Almeno alcune devono essere importanti.

Almeno una può essere segreta.

Le memorie devono avere collegamenti con:

- tratti;
- psicologia;
- famiglia;
- classe;
- comportamento.

memory_type deve essere SOLO:

experience
event
relationship
discovery
training
trauma
achievement
loss
secret


=========================================================
FAMIGLIA
=========================================================

Crea da 0 a 4 familiari quando è plausibile.

Non creare ID.

Usa solamente:

character_name
relationship_type
biological
confirmed

I familiari non devono essere necessariamente tutti vivi.


=========================================================
CONTROLLO FINALE
=========================================================

Prima di restituire il JSON verifica mentalmente:

1. Il personaggio è coerente?
2. Le statistiche hanno senso?
3. I tratti hanno una spiegazione?
4. La psicologia ha una spiegazione?
5. Le memorie spiegano realmente parte della personalità?
6. La classe è coerente?
7. La famiglia è plausibile?
8. Esistono contraddizioni evidenti?
9. Il personaggio sembra una persona reale?
10. Il JSON è valido?
11. Tutti i memory_type sono validi?

Restituisci esclusivamente il JSON.
""".strip()


# =========================================================
# NORMALIZZAZIONE
# =========================================================

def normalize_generated_character(data):

    valid_trait_categories = {
        "personality",
        "behavior",
        "physical",
        "social",
        "mental",
        "combat",
        "racial",
        "custom",
    }

    valid_trait_origins = {
        "initial",
        "experience",
        "event",
        "relationship",
        "training",
        "acquired",
        "unknown",
    }

    valid_psychology_types = {
        "fear",
        "desire",
        "value",
        "belief",
        "trauma",
        "motivation",
        "insecurity",
        "attachment",
        "aversion",
        "ideal",
    }

    valid_stability = {
        "fundamental",
        "strong",
        "flexible",
        "temporary",
    }

    # =====================================================
    # TRAITS
    # =====================================================

    for trait in data.get("traits", []):

        category = trait.get("category")

        if category in valid_psychology_types:

            trait["category"] = "mental"

            print(
                f"\n  Normalizzato trait category: "
                f"{category} -> mental"
            )

        elif category not in valid_trait_categories:

            trait["category"] = "custom"

            print(
                f"\n  Normalizzato trait category: "
                f"{category} -> custom"
            )

        origin = trait.get("origin")

        if origin in valid_psychology_types:

            trait["origin"] = "experience"

            print(
                f"\n  Normalizzato trait origin: "
                f"{origin} -> experience"
            )

        elif origin not in valid_trait_origins:

            trait["origin"] = "unknown"

            print(
                f"\n  Normalizzato trait origin: "
                f"{origin} -> unknown"
            )

        stability = trait.get("stability")

        if stability not in valid_stability:

            trait["stability"] = "flexible"

            print(
                f"\n  Normalizzato trait stability: "
                f"{stability} -> flexible"
            )

    # =====================================================
    # PSYCHOLOGY
    # =====================================================

    for item in data.get("psychology", []):

        psychology_type = item.get("type")

        if psychology_type not in valid_psychology_types:

            item["type"] = "belief"

            print(
                f"\n  Normalizzato psychology type: "
                f"{psychology_type} -> belief"
            )

        origin = item.get("origin")

        if origin in valid_psychology_types:

            item["origin"] = "experience"

            print(
                f"\n  Normalizzato psychology origin: "
                f"{origin} -> experience"
            )

        elif origin not in valid_trait_origins:

            item["origin"] = "unknown"

            print(
                f"\n  Normalizzato psychology origin: "
                f"{origin} -> unknown"
            )

        stability = item.get("stability")

        if stability not in valid_stability:

            item["stability"] = "flexible"

            print(
                f"\n  Normalizzato psychology stability: "
                f"{stability} -> flexible"
            )

    # =====================================================
    # MEMORIE
    # =====================================================

    for memory in data.get("memories", []):

        original_type = memory.get("memory_type")

        normalized_type = normalize_memory_type(
            original_type
        )

        if original_type != normalized_type:

            print(
                f"\n  Normalizzato memory_type: "
                f"{original_type} -> {normalized_type}"
            )

        memory["memory_type"] = normalized_type

    return data


# =========================================================
# VALIDAZIONE
# =========================================================

def validate_generated_character(data):

    if not isinstance(data, dict):

        raise ValueError(
            "La risposta AI non è un oggetto JSON."
        )

    required = (
        "character",
        "statistics",
        "progression",
        "traits",
        "psychology",
        "class",
        "memories",
        "family",
    )

    for key in required:

        if key not in data:

            raise ValueError(
                f"Campo mancante: {key}"
            )

    # =====================================================
    # CHARACTER
    # =====================================================

    character = data["character"]

    if not isinstance(character, dict):

        raise ValueError(
            "character non è un oggetto."
        )

    if not isinstance(
        character.get("name"),
        str
    ) or not character["name"].strip():

        raise ValueError(
            "Nome del personaggio non valido."
        )

    if not isinstance(
        character.get("description"),
        str
    ):

        raise ValueError(
            "Descrizione non valida."
        )

    # =====================================================
    # STATISTICHE
    # =====================================================

    statistics = data["statistics"]

    if not isinstance(statistics, dict):

        raise ValueError(
            "statistics non è un oggetto."
        )

    required_stats = (
        "strength",
        "constitution",
        "speed",
        "intelligence",
        "perception",
        "willpower",
        "luck",
    )

    for stat in required_stats:

        if stat not in statistics:

            raise ValueError(
                f"Statistica mancante: {stat}"
            )

        value = statistics[stat]

        if not isinstance(value, int):

            raise ValueError(
                f"{stat} deve essere un intero."
            )

        if not 1 <= value <= 999:

            raise ValueError(
                f"{stat} fuori limite."
            )

    # =====================================================
    # PROGRESSIONE
    # =====================================================

    progression = data["progression"]

    if not isinstance(progression, dict):

        raise ValueError(
            "progression non è un oggetto."
        )

    level = progression.get("level")
    xp = progression.get("xp")

    if not isinstance(level, int):

        raise ValueError(
            "level non valido."
        )

    if not 1 <= level <= 999:

        raise ValueError(
            "level fuori limite."
        )

    if not isinstance(xp, int):

        raise ValueError(
            "xp non valido."
        )

    if xp < 0:

        raise ValueError(
            "xp non può essere negativo."
        )

    # =====================================================
    # TRATTI
    # =====================================================

    traits = data["traits"]

    if not isinstance(traits, list):

        raise ValueError(
            "traits deve essere una lista."
        )

    if not 4 <= len(traits) <= 7:

        raise ValueError(
            "Il numero di tratti deve essere tra 4 e 7."
        )

    valid_categories = {
        "personality",
        "behavior",
        "physical",
        "social",
        "mental",
        "combat",
        "racial",
        "custom",
    }

    valid_stability = {
        "fundamental",
        "strong",
        "flexible",
        "temporary",
    }

    valid_origins = {
        "initial",
        "experience",
        "event",
        "relationship",
        "training",
        "acquired",
        "unknown",
    }

    for trait in traits:

        if not isinstance(trait, dict):

            raise ValueError(
                "Tratto non valido."
            )

        required_trait_fields = {
            "name",
            "description",
            "category",
            "strength",
            "stability",
            "origin",
            "reason",
        }

        missing = (
            required_trait_fields
            - trait.keys()
        )

        if missing:

            raise ValueError(
                f"Campi mancanti nel tratto: {missing}"
            )

        if not isinstance(
            trait["name"],
            str
        ):

            raise ValueError(
                "Nome tratto non valido."
            )

        if not isinstance(
            trait["description"],
            str
        ):

            raise ValueError(
                "Descrizione tratto non valida."
            )

        if not isinstance(
            trait["reason"],
            str
        ):

            raise ValueError(
                "Reason tratto non valida."
            )

        if trait["category"] not in valid_categories:

            raise ValueError(
                f"Categoria tratto non valida: "
                f"{trait['category']}"
            )

        if trait["stability"] not in valid_stability:

            raise ValueError(
                f"Stabilità tratto non valida: "
                f"{trait['stability']}"
            )

        if trait["origin"] not in valid_origins:

            raise ValueError(
                f"Origine tratto non valida: "
                f"{trait['origin']}"
            )

        strength = trait["strength"]

        if not isinstance(
            strength,
            int
        ):

            raise ValueError(
                "Strength tratto non valida."
            )

        if not 0 <= strength <= 100:

            raise ValueError(
                "Strength tratto fuori limite."
            )

    # =====================================================
    # PSICOLOGIA
    # =====================================================

    psychology = data["psychology"]

    if not isinstance(
        psychology,
        list
    ):

        raise ValueError(
            "psychology deve essere una lista."
        )

    if not 6 <= len(psychology) <= 10:

        raise ValueError(
            "La psicologia deve contenere "
            "tra 6 e 10 elementi."
        )

    valid_types = {
        "fear",
        "desire",
        "value",
        "belief",
        "trauma",
        "motivation",
        "insecurity",
        "attachment",
        "aversion",
        "ideal",
    }

    for item in psychology:

        if not isinstance(
            item,
            dict
        ):

            raise ValueError(
                "Elemento psicologico non valido."
            )

        required_psychology_fields = {
            "type",
            "name",
            "description",
            "strength",
            "stability",
            "origin",
            "reason",
        }

        missing = (
            required_psychology_fields
            - item.keys()
        )

        if missing:

            raise ValueError(
                f"Campi mancanti nella psicologia: "
                f"{missing}"
            )

        if item["type"] not in valid_types:

            raise ValueError(
                f"Tipo psicologico non valido: "
                f"{item['type']}"
            )

        if not isinstance(
            item["name"],
            str
        ):

            raise ValueError(
                "Nome psicologico non valido."
            )

        if not isinstance(
            item["description"],
            str
        ):

            raise ValueError(
                "Descrizione psicologica non valida."
            )

        if not isinstance(
            item["reason"],
            str
        ):

            raise ValueError(
                "Reason psicologica non valida."
            )

        if item["stability"] not in valid_stability:

            raise ValueError(
                "Stabilità psicologica non valida."
            )

        if item["origin"] not in valid_origins:

            raise ValueError(
                "Origine psicologica non valida."
            )

        strength = item["strength"]

        if not isinstance(
            strength,
            int
        ):

            raise ValueError(
                "Strength psicologica non valida."
            )

        if not 0 <= strength <= 100:

            raise ValueError(
                "Strength psicologica fuori limite."
            )

    # =====================================================
    # CLASSE
    # =====================================================

    class_data = data["class"]

    if not isinstance(
        class_data,
        dict
    ):

        raise ValueError(
            "class non valido."
        )

    if not isinstance(
        class_data.get("name"),
        str
    ) or not class_data["name"].strip():

        raise ValueError(
            "La classe non ha un nome."
        )

    if not isinstance(
        class_data.get("description"),
        str
    ):

        raise ValueError(
            "Descrizione classe non valida."
        )

    if not isinstance(
        class_data.get("category"),
        str
    ):

        raise ValueError(
            "Categoria classe non valida."
        )

    if not isinstance(
        class_data.get("level"),
        int
    ):

        raise ValueError(
            "Livello classe non valido."
        )

    if not 1 <= class_data["level"] <= 999:

        raise ValueError(
            "Livello classe fuori limite."
        )

    if not isinstance(
        class_data.get("experience"),
        int
    ):

        raise ValueError(
            "Esperienza classe non valida."
        )

    if class_data["experience"] < 0:

        raise ValueError(
            "Esperienza classe negativa."
        )

    if not isinstance(
        class_data.get("is_primary"),
        bool
    ):

        raise ValueError(
            "is_primary deve essere boolean."
        )

    # =====================================================
    # MEMORIE
    # =====================================================

    memories = data["memories"]

    if not isinstance(
        memories,
        list
    ):

        raise ValueError(
            "memories deve essere una lista."
        )

    if len(memories) < 5:

        raise ValueError(
            "Devono esserci almeno 5 memorie."
        )

    for memory in memories:

        if not isinstance(
            memory,
            dict
        ):

            raise ValueError(
                "Memoria non valida."
            )

        required_memory_fields = {
            "content",
            "memory_type",
            "importance",
            "is_secret",
        }

        missing = (
            required_memory_fields
            - memory.keys()
        )

        if missing:

            raise ValueError(
                f"Campi mancanti nella memoria: "
                f"{missing}"
            )

        if not isinstance(
            memory.get("content"),
            str
        ) or not memory["content"].strip():

            raise ValueError(
                "Memoria senza contenuto."
            )

        if memory["memory_type"] not in VALID_MEMORY_TYPES:

            raise ValueError(
                f"Tipo di memoria non valido: "
                f"{memory['memory_type']}"
            )

        importance = memory["importance"]

        if not isinstance(
            importance,
            int
        ):

            raise ValueError(
                "Importance memoria non valida."
            )

        if not 1 <= importance <= 10:

            raise ValueError(
                "Importance memoria fuori limite."
            )

        if not isinstance(
            memory["is_secret"],
            bool
        ):

            raise ValueError(
                "is_secret deve essere boolean."
            )

    # =====================================================
    # FAMIGLIA
    # =====================================================

    family = data["family"]

    if not isinstance(
        family,
        list
    ):

        raise ValueError(
            "family deve essere una lista."
        )

    if not 0 <= len(family) <= 4:

        raise ValueError(
            "La famiglia deve contenere da 0 a 4 elementi."
        )

    for member in family:

        if not isinstance(
            member,
            dict
        ):

            raise ValueError(
                "Familiare non valido."
            )

        required_family_fields = {
            "character_name",
            "relationship_type",
            "biological",
            "confirmed",
        }

        missing = (
            required_family_fields
            - member.keys()
        )

        if missing:

            raise ValueError(
                f"Campi mancanti nel familiare: "
                f"{missing}"
            )

        if not isinstance(
            member["character_name"],
            str
        ):

            raise ValueError(
                "character_name familiare non valido."
            )

        if not isinstance(
            member["relationship_type"],
            str
        ):

            raise ValueError(
                "relationship_type familiare non valido."
            )

        if not isinstance(
            member["biological"],
            bool
        ):

            raise ValueError(
                "biological deve essere boolean."
            )

        if not isinstance(
            member["confirmed"],
            bool
        ):

            raise ValueError(
                "confirmed deve essere boolean."
            )

    return True


# =========================================================
# GENERAZIONE
# =========================================================

def generate_character_with_ai():

    print("=" * 70)
    print("GENERAZIONE PERSONAGGIO TRAMITE AI")
    print("=" * 70)

    # -----------------------------------------------------
    # AVVIO
    # -----------------------------------------------------

    show_progress(
        0,
        "Avvio generazione..."
    )

    # -----------------------------------------------------
    # OLLAMA
    # -----------------------------------------------------

    show_progress(
        10,
        "Invio richiesta a Ollama..."
    )

    response = ask_ollama(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=USER_PROMPT
    )

    show_progress(
        45,
        "Risposta ricevuta..."
    )

    # -----------------------------------------------------
    # CONTROLLO RISPOSTA
    # -----------------------------------------------------

    if not isinstance(response, str):

        raise ValueError(
            "Ollama non ha restituito una stringa."
        )

    response = response.strip()

    if not response:

        raise ValueError(
            "Ollama ha restituito una risposta vuota."
        )

    # -----------------------------------------------------
    # PARSING
    # -----------------------------------------------------

    show_progress(
        55,
        "Parsing JSON..."
    )

    try:

        data = json.loads(response)

    except json.JSONDecodeError as error:

        print("\n")
        print("=" * 70)
        print("ERRORE JSON")
        print("=" * 70)

        print(response)

        print("=" * 70)

        raise ValueError(
            "L'AI non ha restituito JSON valido."
        ) from error

    # -----------------------------------------------------
    # NORMALIZZAZIONE
    # -----------------------------------------------------

    show_progress(
        65,
        "Normalizzazione dati..."
    )

    data = normalize_generated_character(
        data
    )

    # -----------------------------------------------------
    # VALIDAZIONE
    # -----------------------------------------------------

    show_progress(
        80,
        "Validazione struttura..."
    )

    validate_generated_character(
        data
    )

    # -----------------------------------------------------
    # COMPLETATO
    # -----------------------------------------------------

    show_progress(
        100,
        "Generazione completata."
    )

    print("\n")

    return data


# =========================================================
# SALVATAGGIO DATABASE
# =========================================================

def save_generated_character(data):

    print("\n")
    print("=" * 70)
    print("SALVATAGGIO DATABASE")
    print("=" * 70)

    # -----------------------------------------------------
    # PERSONAGGIO
    # -----------------------------------------------------

    show_progress(
        85,
        "Creazione personaggio..."
    )

    character_data = data["character"]

    character_id = create_character(
        name=character_data["name"],
        description=character_data["description"]
    )

    # -----------------------------------------------------
    # STATISTICHE
    # -----------------------------------------------------

    show_progress(
        87,
        "Salvataggio statistiche..."
    )

    create_character_statistics(
        character_id=character_id,
        **data["statistics"]
    )

    # -----------------------------------------------------
    # PROGRESSIONE
    # -----------------------------------------------------

    show_progress(
        89,
        "Salvataggio progressione..."
    )

    progression = data["progression"]

    level = progression["level"]

    xp_required = calculate_xp_required(
        level
    )

    create_character_progression(
        character_id=character_id,
        level=level,
        xp=progression["xp"],
        xp_required=xp_required
    )

    # -----------------------------------------------------
    # TRATTI
    # -----------------------------------------------------

    traits = data["traits"]

    for index, trait in enumerate(traits):

        percent = 90 + int(
            ((index + 1) / len(traits)) * 2
        )

        show_progress(
            percent,
            "Salvataggio tratti..."
        )

        create_character_trait(
            character_id=character_id,
            name=trait["name"],
            description=trait["description"],
            category=trait["category"],
            strength=trait["strength"],
            stability=trait["stability"],
            origin=trait["origin"],
            reason=trait["reason"]
        )

    # -----------------------------------------------------
    # PSICOLOGIA
    # -----------------------------------------------------

    psychology = data["psychology"]

    for index, item in enumerate(psychology):

        percent = 92 + int(
            ((index + 1) / len(psychology)) * 2
        )

        show_progress(
            percent,
            "Salvataggio psicologia..."
        )

        create_character_psychology(
            character_id=character_id,
            type=item["type"],
            name=item["name"],
            description=item["description"],
            strength=item["strength"],
            stability=item["stability"],
            origin=item["origin"],
            reason=item["reason"]
        )

    # -----------------------------------------------------
    # CLASSE
    # -----------------------------------------------------

    show_progress(
        95,
        "Salvataggio classe..."
    )

    class_data = data["class"]

    existing_class = find_class(
        class_data["name"]
    )

    if existing_class is None:

        class_id = create_class(
            name=class_data["name"],
            description=class_data["description"],
            category=class_data["category"]
        )

    else:

        class_id = existing_class["id"]

    add_character_class(
        character_id=character_id,
        class_id=class_id,
        level=class_data["level"],
        experience=class_data["experience"],
        is_primary=class_data["is_primary"]
    )

    # -----------------------------------------------------
    # MEMORIE
    # -----------------------------------------------------

    memories = data["memories"]

    for index, memory in enumerate(memories):

        percent = 96 + int(
            ((index + 1) / len(memories)) * 2
        )

        show_progress(
            percent,
            "Salvataggio memorie..."
        )

        memory_type = normalize_memory_type(
            memory["memory_type"]
        )

        create_memory(
            character_id=character_id,
            content=memory["content"],
            memory_type=memory_type,
            importance=memory["importance"],
            is_secret=memory["is_secret"]
        )

    # -----------------------------------------------------
    # FAMIGLIA
    # -----------------------------------------------------

    show_progress(
        99,
        "Salvataggio famiglia..."
    )

    # Per ora la famiglia viene solamente generata.
    #
    # Non vengono creati record perché il JSON
    # contiene solamente il nome del familiare.
    #
    # In futuro sarà possibile creare un sistema
    # di relazioni/famiglia persistente.

    for member in data["family"]:

        _ = member

    # -----------------------------------------------------
    # COMPLETATO
    # -----------------------------------------------------

    show_progress(
        100,
        "Salvataggio completato."
    )

    print("\n")

    return character_id


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    try:

        # =================================================
        # GENERAZIONE
        # =================================================

        generated_data = (
            generate_character_with_ai()
        )

        # =================================================
        # JSON
        # =================================================

        print("\n")
        print("=" * 70)
        print("JSON GENERATO")
        print("=" * 70)

        print(
            json.dumps(
                generated_data,
                indent=4,
                ensure_ascii=False
            )
        )

        # =================================================
        # SALVATAGGIO
        # =================================================

        character_id = (
            save_generated_character(
                generated_data
            )
        )

        # =================================================
        # RISULTATO
        # =================================================

        print("\n")
        print("=" * 70)
        print("PERSONAGGIO COMPLETAMENTE GENERATO")
        print("=" * 70)

        character_data = (
            generated_data["character"]
        )

        progression = (
            generated_data["progression"]
        )

        class_data = (
            generated_data["class"]
        )

        print(
            f"\nID: {character_id}"
        )

        print(
            f"Nome: "
            f"{character_data['name']}"
        )

        print(
            f"Livello: "
            f"{progression['level']}"
        )

        print(
            f"Classe: "
            f"{class_data['name']}"
        )

        print("\nDescrizione:")

        print(
            character_data["description"]
        )

        print("\n")

        print("=" * 70)
        print("TEST TERMINATO")
        print("=" * 70)

        print(
            f"Personaggio creato con ID: "
            f"{character_id}"
        )

    except Exception as error:

        print("\n")
        print("=" * 70)
        print("ERRORE DURANTE IL TEST")
        print("=" * 70)

        print(
            f"\n{type(error).__name__}: "
            f"{error}"
        )

        print("=" * 70)

        raise