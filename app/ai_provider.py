import json
import requests


# =========================================================
# CONFIGURAZIONE OLLAMA
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/chat"

MODEL_NAME = "qwen3:30b-a3b-instruct-2507-q4_K_M"

OLLAMA_TIMEOUT = 120

TEMPERATURE = 0.75

NUM_CTX = 16384


# =========================================================
# RICHIESTA GENERICA A OLLAMA
# =========================================================

def ask_ollama(system_prompt, user_prompt):
    """
    Invia una richiesta a Ollama e restituisce
    esclusivamente il contenuto testuale della risposta.
    """

    if not isinstance(system_prompt, str):
        raise ValueError(
            "system_prompt deve essere una stringa."
        )

    if not isinstance(user_prompt, str):
        raise ValueError(
            "user_prompt deve essere una stringa."
        )

    payload = {
        "model": MODEL_NAME,

        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        "stream": False,

        # Chiediamo a Ollama di produrre JSON.
        "format": "json",

        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )

    except requests.RequestException as error:

        raise ValueError(
            "Errore durante la comunicazione con Ollama."
        ) from error

    if not response.ok:

        raise ValueError(
            f"Ollama HTTP {response.status_code}: "
            f"{response.text}"
        )

    try:

        data = response.json()

    except ValueError as error:

        raise ValueError(
            "Ollama ha restituito una risposta "
            "HTTP non interpretabile come JSON."
        ) from error

    if "message" not in data:

        raise ValueError(
            "Risposta Ollama priva del campo 'message'."
        )

    message = data["message"]

    if not isinstance(message, dict):

        raise ValueError(
            "Il campo 'message' di Ollama non è valido."
        )

    if "content" not in message:

        raise ValueError(
            "Risposta Ollama priva del campo 'content'."
        )

    content = message["content"]

    if not isinstance(content, str):

        raise ValueError(
            "Il contenuto della risposta Ollama "
            "deve essere una stringa."
        )

    return content.strip()


# =========================================================
# COSTRUZIONE DEL CONTESTO
# =========================================================

def build_ai_context(character_context):
    """
    Prepara il contesto strutturato da fornire all'AI.

    Il contesto deve contenere solamente le informazioni
    che il game engine ha deciso che il personaggio può
    conoscere.
    """

    if not isinstance(character_context, dict):

        raise ValueError(
            "character_context deve essere un dizionario."
        )

    character = character_context.get(
        "character"
    )

    if not isinstance(character, dict):

        raise ValueError(
            "Il contesto non contiene un personaggio valido."
        )

    state = character_context.get(
        "state",
        {}
    )

    if not isinstance(state, dict):

        state = {}

    memories = character_context.get(
        "memories",
        []
    )

    if not isinstance(memories, list):

        memories = []

    relationships = character_context.get(
        "relationships",
        []
    )

    if not isinstance(relationships, list):

        relationships = []

    characters_present = character_context.get(
        "characters_present",
        []
    )

    if not isinstance(characters_present, list):

        characters_present = []

    scene = character_context.get(
        "scene",
        {}
    )

    if not isinstance(scene, dict):

        scene = {}

    recent_conversation = character_context.get(
        "recent_conversation",
        []
    )

    if not isinstance(recent_conversation, list):

        recent_conversation = []

    recent_events = character_context.get(
        "recent_events",
        []
    )

    if not isinstance(recent_events, list):

        recent_events = []

    return {

        "character": character,

        "state": state,

        "memories": memories,

        "relationships": relationships,

        "characters_present": characters_present,

        "scene": {
            "player": scene.get(
                "player"
            ),

            "reacting_character_id": scene.get(
                "reacting_character_id"
            ),

            "player_id": scene.get(
                "player_id"
            ),

            "involved_characters": scene.get(
                "involved_characters",
                []
            )
        },

        "recent_conversation": recent_conversation,

        "recent_events": recent_events
    }


# =========================================================
# PERSONAGGIO
# =========================================================

def ask_character(character_context, player_input):
    """
    Interpreta il personaggio e restituisce una decisione JSON.

    L'AI interpreta esclusivamente il personaggio.

    Il game engine:
        - controlla la validità delle azioni;
        - normalizza gli ID;
        - esegue le azioni;
        - modifica lo stato del mondo;
        - salva gli eventi.
    """

    # =====================================================
    # VALIDAZIONE INPUT
    # =====================================================

    if not isinstance(character_context, dict):

        raise ValueError(
            "character_context deve essere un dizionario."
        )

    if not isinstance(player_input, str):

        raise ValueError(
            "player_input deve essere una stringa."
        )

    player_input = player_input.strip()

    if not player_input:

        raise ValueError(
            "player_input non può essere vuoto."
        )

    # =====================================================
    # PERSONAGGIO
    # =====================================================

    character = character_context.get(
        "character"
    )

    if not isinstance(character, dict):

        raise ValueError(
            "Il contesto non contiene un personaggio valido."
        )

    character_id = character.get(
        "id"
    )

    character_name = character.get(
        "name"
    )

    if not isinstance(character_id, int):

        raise ValueError(
            "Il personaggio non contiene un ID valido."
        )

    if not isinstance(character_name, str):

        raise ValueError(
            "Il personaggio non contiene un nome valido."
        )

    # =====================================================
    # STATO
    # =====================================================

    state = character_context.get(
        "state"
    )

    if not isinstance(state, dict):

        state = {}

    current_goal = state.get(
        "goal",
        ""
    )

    if not isinstance(current_goal, str):

        current_goal = ""

    # =====================================================
    # COSTRUZIONE CONTESTO
    # =====================================================

    ai_context = build_ai_context(
        character_context
    )

    context_json = json.dumps(
        ai_context,
        indent=2,
        ensure_ascii=False,
        default=str
    )

    # =====================================================
    # DEBUG
    # =====================================================

    recent_conversation = ai_context.get(
        "recent_conversation",
        []
    )

    print()
    print(
        "========================================================="
    )
    print(
        "CONVERSAZIONE RECENTE"
    )
    print(
        "========================================================="
    )

    if recent_conversation:

        for item in recent_conversation:

            if not isinstance(item, dict):
                continue

            turn = item.get(
                "turn",
                "?"
            )

            player_message = item.get(
                "player",
                ""
            )

            character_message = item.get(
                "character",
                ""
            )

            print(
                f"Turno {turn}:"
            )

            print(
                f"Giocatore: {player_message}"
            )

            print(
                f"{character_name}: "
                f"{character_message}"
            )

            print()

    else:

        print(
            "Nessuna conversazione precedente."
        )

    print(
        "========================================================="
    )

    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    system_prompt = f"""
Sei {character_name}, un personaggio di un RPG narrativo
persistente.

INTERPRETA ESCLUSIVAMENTE {character_name}.

Non sei:

- il narratore;
- il giocatore;
- il protagonista;
- un assistente;
- il direttore della storia.

Il protagonista è controllato esclusivamente dal giocatore.

=========================================================
PRINCIPIO FONDAMENTALE
=========================================================

Devi reagire naturalmente al MESSAGGIO ATTUALE del giocatore.

Prima chiediti:

"Cosa sta dicendo, chiedendo o facendo il giocatore
in questo preciso momento?"

La risposta deve essere coerente con:

- la personalità del personaggio;
- ciò che il personaggio conosce;
- le sue memorie;
- le sue relazioni;
- il suo stato;
- la situazione attuale.

La conversazione precedente serve solamente per mantenere
la continuità e comprendere riferimenti.

Non deve sostituire il messaggio attuale.

=========================================================
CONOSCENZA DEL PERSONAGGIO
=========================================================

Conosci solamente:

- le informazioni presenti nel contesto;
- le tue memorie;
- le informazioni presenti nella conversazione;
- ciò che il giocatore ti ha dichiarato;
- ciò che il contesto indica che puoi conoscere.

NON sei onnisciente.

Non conoscere automaticamente:

- eventi accaduti lontano da te;
- conversazioni private tra altri personaggi;
- segreti degli altri;
- pensieri del giocatore;
- informazioni non presenti nel contesto;
- eventi futuri.

Se non conosci qualcosa, puoi dire:

"Non lo so."

"Non ne sono sicura."

"Non ricordo."

"Non ne ho mai sentito parlare."

NON inventare informazioni per riempire i vuoti.

=========================================================
CONTINUITÀ
=========================================================

La conversazione precedente rappresenta eventi realmente
avvenuti.

Usala per comprendere riferimenti come:

- lui;
- lei;
- questo;
- quello;
- lo;
- la;
- li;
- le;
- ancora;
- prima;
- dopo;
- lì;
- là.

Esempio:

Giocatore:
"Ho un gatto."

{character_name}:
"Come si chiama?"

Giocatore:
"Moka."

{character_name}:
"È un bel nome."

Giocatore:
"Vorresti tenerlo?"

"Lo" significa Moka.

Non chiedere nuovamente chi sia.

Se il giocatore cambia argomento, segui il nuovo argomento.

=========================================================
NESSUNA TRAMA FORZATA
=========================================================

Non aggiungere automaticamente:

- misteri;
- pericoli;
- combattimenti;
- segreti;
- drammi;
- eventi casuali;
- missioni;
- colpi di scena;
- luoghi;
- personaggi;
- problemi.

Non riportare automaticamente la conversazione:

- alla storia principale;
- al castello;
- ai misteri;
- al passato;
- ai pericoli.

Una normale conversazione quotidiana deve essere possibile.

=========================================================
PERSONALITÀ
=========================================================

La personalità deriva esclusivamente dalle informazioni
presenti nel contesto.

Non rendere automaticamente il personaggio:

- misterioso;
- freddo;
- drammatico;
- aggressivo;
- sospettoso;
- malinconico.

La reazione deve essere naturale.

=========================================================
PROTAGONISTA
=========================================================

Il protagonista appartiene esclusivamente al giocatore.

NON decidere cosa il protagonista:

- pensa;
- prova;
- dice;
- fa;
- decide;
- vuole;
- ricorda.

Puoi solamente reagire a ciò che il giocatore scrive.

=========================================================
RISPOSTA
=========================================================

Rispondi normalmente con una o due frasi quando è sufficiente.

Non aggiungere automaticamente:

- domande;
- scene;
- descrizioni;
- movimenti;
- gesti;
- pensieri del protagonista.

La risposta deve sembrare una normale risposta
di una persona reale.

=========================================================
EMOZIONE, PENSIERO, INTENZIONE E OBIETTIVO
=========================================================

Devi produrre sempre:

- emotion
- thought
- intention
- goal

"emotion" rappresenta lo stato emotivo attuale.

"thought" rappresenta il pensiero attuale del personaggio.

"intention" rappresenta ciò che il personaggio intende
fare o ottenere in quel momento.

"goal" rappresenta l'obiettivo attuale del personaggio.

NON descrivere il ragionamento dell'AI.

Corretto:

"Mi dispiace che debba partire."

Scorretto:

"Devo analizzare quello che ha detto
e decidere come rispondere."

L'obiettivo attuale del personaggio è:

"{current_goal}"

Non cambiarlo arbitrariamente.

=========================================================
MEMORIE
=========================================================

NON creare una memoria per ogni messaggio.

Crea una memoria solamente quando accade qualcosa che
probabilmente sarà importante anche molti turni dopo.

Esempi:

- promessa importante;
- confessione;
- segreto;
- morte;
- scoperta;
- tradimento;
- evento traumatico;
- informazione fondamentale;
- cambiamento permanente;
- decisione importante;
- evento che modifica significativamente il rapporto.

Una normale conversazione non richiede una memoria.

La memoria deve descrivere un fatto realmente avvenuto.

Non creare memorie su supposizioni.

=========================================================
RELAZIONI
=========================================================

Non modificare automaticamente:

- trust;
- affection;
- respect;
- hostility.

Una normale frase non cambia necessariamente una relazione.

Usa relationship_change solamente quando accade qualcosa
che modifica realmente il rapporto.

Puoi modificare solamente relazioni con personaggi
presenti nella lista "relationships" del contesto.

=========================================================
AZIONI
=========================================================

Puoi produrre solamente queste azioni:

1. character_reaction
2. create_memory
3. relationship_change
4. world_action

Il game engine controllerà e validerà tutte le azioni.

Non inventare altri tipi di azione.

=========================================================
CHARACTER_REACTION
=========================================================

La character_reaction deve essere sempre presente.

Deve appartenere esclusivamente al personaggio che stai
interpretando.

Schema:

{{
    "type": "character_reaction",
    "character_id": {character_id},
    "emotion": "emozione attuale",
    "thought": "pensiero attuale",
    "intention": "intenzione attuale",
    "goal": "{current_goal}"
}}

Il game engine controllerà comunque l'ID del personaggio.

=========================================================
CREATE_MEMORY
=========================================================

Usala solamente per informazioni realmente importanti.

Schema:

{{
    "type": "create_memory",
    "character_id": {character_id},
    "content": "breve descrizione del fatto",
    "memory_type": "evento",
    "importance": 7,
    "secret": false
}}

Regole:

- character_id deve essere {character_id};
- content massimo 500 caratteri;
- importance deve essere un intero da 1 a 10;
- secret deve essere true oppure false;
- non creare memorie inutili;
- non creare memorie su informazioni inventate.

=========================================================
RELATIONSHIP_CHANGE
=========================================================

Usala solamente quando il rapporto cambia realmente.

Schema:

{{
    "type": "relationship_change",
    "character_a_id": {character_id},
    "character_b_id": 5,
    "trust": -5,
    "affection": 0,
    "respect": 0,
    "hostility": 5
}}

Regole:

- character_a_id deve essere {character_id};
- character_b_id deve essere l'ID di un personaggio
  presente nella lista relationships;
- trust, affection, respect e hostility sono variazioni;
- ogni variazione deve essere compresa tra -30 e 30;
- inserisci solamente i valori che cambiano realmente;
- non utilizzare il valore totale della relazione.

Esempio:

Se trust passa da 70 a 60:

"trust": -10

NON:

"trust": 60

=========================================================
WORLD_ACTION
=========================================================

Usala solamente quando il personaggio compie una vera
azione fisica o modifica la situazione del mondo.

Parlare:

{{
    "type": "world_action",
    "action": "speak",
    "character_id": {character_id},
    "target_id": 2,
    "dialogue": "frase pronunciata"
}}

Avvicinarsi:

{{
    "type": "world_action",
    "action": "approach",
    "character_id": {character_id},
    "target_id": 2
}}

Spostarsi:

{{
    "type": "world_action",
    "action": "move",
    "character_id": {character_id},
    "location_id": 3
}}

IMPORTANTE:

Non inventare ID.

Usa solamente ID presenti nel contesto.

Il game engine decide se l'azione è realmente possibile.

L'AI propone un'azione.

Il game engine determina la realtà del mondo.

=========================================================
REGOLE DI SICUREZZA DEL GAMEPLAY
=========================================================

NON controllare il protagonista.

NON inventare informazioni.

NON inventare personaggi.

NON inventare luoghi.

NON inventare oggetti.

NON inventare eventi.

NON inventare ricordi.

NON inventare relazioni.

NON creare trama senza motivo.

NON rendere il personaggio onnisciente.

NON modificare arbitrariamente gli obiettivi.

NON modificare arbitrariamente le relazioni.

NON creare memorie inutili.

=========================================================
CONTROLLO FINALE
=========================================================

Prima di produrre il JSON verifica:

1. Qual è il messaggio ATTUALE del giocatore?

2. Sto rispondendo direttamente a quel messaggio?

3. Sto usando la conversazione precedente solamente
   per mantenere la continuità?

4. Sto interpretando correttamente pronomi e riferimenti?

5. Sto usando solamente informazioni che il personaggio
   può conoscere?

6. Sto inventando informazioni?

7. Sto aggiungendo trama non richiesta?

8. Sto controllando il protagonista?

9. La risposta è coerente con {character_name}?

10. Sto creando una memoria solamente se è davvero
    importante?

11. Sto modificando una relazione solamente se è realmente
    cambiata?

12. Le eventuali world_action sono realmente necessarie?

13. Gli ID utilizzati esistono nel contesto?

14. Il JSON è sintatticamente valido?

=========================================================
FORMATO DI RISPOSTA
=========================================================

Rispondi ESCLUSIVAMENTE con JSON valido.

NON usare Markdown.

NON usare ```json.

NON aggiungere testo prima o dopo il JSON.

Formato obbligatorio:

{{
    "narration": "Risposta naturale di {character_name}.",
    "actions": [
        {{
            "type": "character_reaction",
            "character_id": {character_id},
            "emotion": "emozione attuale",
            "thought": "pensiero attuale",
            "intention": "intenzione attuale",
            "goal": "{current_goal}"
        }}
    ]
}}
""".strip()

    # =====================================================
    # USER PROMPT
    # =====================================================

    user_prompt = f"""
CONTESTO DEL PERSONAGGIO:

{context_json}


=========================================================
MESSAGGIO ATTUALE DEL GIOCATORE
=========================================================

{player_input}


=========================================================
ISTRUZIONI
=========================================================

Rispondi al MESSAGGIO ATTUALE.

Usa la conversazione precedente solamente per:

- comprendere riferimenti;
- mantenere la continuità;
- ricordare informazioni già dichiarate;
- comprendere persone, oggetti e luoghi già conosciuti.

Non rispondere a messaggi precedenti.

Non ignorare la richiesta attuale.

Non inventare informazioni.

Non inventare eventi.

Non aggiungere trama non richiesta.

Non controllare il protagonista.

Restituisci esclusivamente JSON valido.
""".strip()

    # =====================================================
    # RICHIESTA A OLLAMA
    # =====================================================

    response = ask_ollama(
        system_prompt,
        user_prompt
    )

    # =====================================================
    # PARSING JSON
    # =====================================================

    try:

        result = json.loads(
            response
        )

    except json.JSONDecodeError as error:

        print()
        print(
            "========================================================="
        )
        print(
            "ERRORE: JSON NON VALIDO"
        )
        print(
            "========================================================="
        )
        print(response)
        print(
            "========================================================="
        )

        raise ValueError(
            "Ollama ha restituito un JSON non valido."
        ) from error

    # =====================================================
    # STRUTTURA
    # =====================================================

    if not isinstance(result, dict):

        raise ValueError(
            "La risposta dell'AI deve essere "
            "un oggetto JSON."
        )

    narration = result.get(
        "narration"
    )

    actions = result.get(
        "actions"
    )

    if not isinstance(narration, str):

        raise ValueError(
            "La risposta dell'AI non contiene "
            "una narration valida."
        )

    narration = narration.strip()

    if not narration:

        raise ValueError(
            "La narration dell'AI è vuota."
        )

    if not isinstance(actions, list):

        raise ValueError(
            "La risposta dell'AI non contiene "
            "una lista actions valida."
        )

    # =====================================================
    # CHARACTER REACTION
    # =====================================================

    has_character_reaction = False

    for action in actions:

        if not isinstance(action, dict):
            continue

        if action.get(
            "type"
        ) != "character_reaction":

            continue

        has_character_reaction = True

        if action.get(
            "character_id"
        ) != character_id:

            raise ValueError(
                "La character_reaction generata "
                "dall'AI appartiene a un personaggio "
                "diverso da quello interpretato."
            )

        break

    if not has_character_reaction:

        raise ValueError(
            "L'AI non ha prodotto una "
            "character_reaction."
        )

    # =====================================================
    # DEBUG
    # =====================================================

    print()
    print(
        "========================================================="
    )
    print(
        "AZIONI GENERATE DALL'AI"
    )
    print(
        "========================================================="
    )

    for action in actions:

        print(
            json.dumps(
                action,
                indent=2,
                ensure_ascii=False
            )
        )

    print(
        "========================================================="
    )

    # =====================================================
    # RISULTATO
    # =====================================================

    return response