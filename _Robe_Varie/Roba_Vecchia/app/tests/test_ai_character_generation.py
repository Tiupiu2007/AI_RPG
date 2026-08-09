from _Robe_Varie.Roba_Vecchia.app.database import get_connection

from _Robe_Varie.Roba_Vecchia.app.characters.character import create_character
from _Robe_Varie.Roba_Vecchia.app.characters.character_stats import (
    create_character_statistics,
    get_character_statistics,
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_progression import (
    create_character_progression,
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

from _Robe_Varie.Roba_Vecchia.app.characters.character_family import (
    create_family_relationship,
)


# =========================================================
# CONFIGURAZIONE TEST
# =========================================================

CHARACTER_NAME = "Elian Veyr"

CHARACTER_DESCRIPTION = (
    "Un giovane uomo tranquillo e riflessivo che vive in una "
    "piccola città. Tende a osservare le persone prima di "
    "fidarsi di loro."
)


# =========================================================
# CREAZIONE PERSONAGGIO
# =========================================================

def create_complete_character():

    print("=" * 60)
    print("CREAZIONE PERSONAGGIO COMPLETO")
    print("=" * 60)

    # -----------------------------------------------------
    # PERSONAGGIO BASE
    # -----------------------------------------------------

    print("\n[1/7] Creazione personaggio...")

    character_id = create_character(
        name=CHARACTER_NAME,
        description=CHARACTER_DESCRIPTION
    )

    print(f"  Character ID: {character_id}")

    # -----------------------------------------------------
    # STATISTICHE
    # -----------------------------------------------------

    print("\n[2/7] Creazione statistiche...")

    create_character_statistics(
        character_id=character_id,

        strength=42,
        constitution=55,
        speed=61,
        intelligence=78,
        perception=72,
        willpower=67,
        luck=48
    )

    statistics = get_character_statistics(
        character_id
    )

    print("  Statistiche:")

    for name, value in statistics.items():

        if name == "character_id":
            continue

        print(
            f"    {name}: {value}"
        )

    # -----------------------------------------------------
    # PROGRESSIONE
    # -----------------------------------------------------

    print("\n[3/7] Creazione progressione...")

    create_character_progression(
        character_id=character_id,
        level=3,
        xp=120,
        xp_required=519
    )

    print("  Livello: 3")
    print("  XP: 120")
    print("  XP richiesta: 519")

    # -----------------------------------------------------
    # TRATTI
    # -----------------------------------------------------

    print("\n[4/7] Creazione tratti...")

    traits = [

        {
            "name": "Paziente",
            "description": (
                "Tende ad aspettare e osservare prima di agire."
            ),
            "category": "personality",
            "strength": 82,
            "stability": "strong",
            "origin": "initial",
            "reason": (
                "Ha sviluppato questa caratteristica "
                "durante l'infanzia."
            )
        },

        {
            "name": "Osservatore",
            "description": (
                "Presta molta attenzione ai dettagli "
                "e al comportamento degli altri."
            ),
            "category": "mental",
            "strength": 74,
            "stability": "strong",
            "origin": "experience",
            "reason": (
                "Ha imparato che osservare gli altri "
                "gli permette di evitare problemi."
            )
        },

        {
            "name": "Protettivo",
            "description": (
                "Tende a proteggere le persone a cui tiene."
            ),
            "category": "behavior",
            "strength": 68,
            "stability": "flexible",
            "origin": "relationship",
            "reason": (
                "Una persona importante per lui gli ha "
                "insegnato il valore della protezione."
            )
        },

        {
            "name": "Resistente",
            "description": (
                "Riesce a sopportare situazioni fisicamente "
                "faticose più a lungo della media."
            ),
            "category": "physical",
            "strength": 61,
            "stability": "strong",
            "origin": "training",
            "reason": (
                "Ha svolto allenamento fisico per diversi anni."
            )
        },

    ]

    for trait in traits:

        trait_id = create_character_trait(
            character_id=character_id,
            **trait
        )

        print(
            f"  Creato tratto: "
            f"{trait['name']} "
            f"(ID {trait_id})"
        )

    # -----------------------------------------------------
    # PSICOLOGIA
    # -----------------------------------------------------

    print("\n[5/7] Creazione psicologia...")

    psychology = [

        {
            "type": "fear",
            "name": "Perdere le persone importanti",
            "description": (
                "Ha paura che le persone a cui si affeziona "
                "possano scomparire dalla sua vita."
            ),
            "strength": 76,
            "stability": "strong",
            "origin": "experience",
            "reason": (
                "Ha già vissuto una perdita importante."
            )
        },

        {
            "type": "desire",
            "name": "Essere compreso",
            "description": (
                "Desidera trovare qualcuno capace di "
                "comprendere veramente il suo modo di pensare."
            ),
            "strength": 64,
            "stability": "flexible",
            "origin": "initial",
            "reason": (
                "Ha sempre avuto difficoltà a esprimere "
                "ciò che prova."
            )
        },

        {
            "type": "value",
            "name": "Lealtà",
            "description": (
                "Considera la lealtà una delle qualità "
                "più importanti in una persona."
            ),
            "strength": 88,
            "stability": "fundamental",
            "origin": "initial",
            "reason": (
                "È uno dei principi fondamentali con cui "
                "è cresciuto."
            )
        },

        {
            "type": "belief",
            "name": "Le persone possono cambiare",
            "description": (
                "Crede che una persona non debba essere "
                "definita solamente dai propri errori."
            ),
            "strength": 71,
            "stability": "strong",
            "origin": "experience",
            "reason": (
                "Una sua esperienza passata gli ha fatto "
                "cambiare opinione sulle persone."
            )
        },

        {
            "type": "insecurity",
            "name": "Non essere abbastanza",
            "description": (
                "A volte teme di non essere capace di "
                "fare ciò che gli altri si aspettano."
            ),
            "strength": 59,
            "stability": "flexible",
            "origin": "experience",
            "reason": (
                "Ha ricevuto spesso aspettative elevate "
                "durante la crescita."
            )
        },

        {
            "type": "motivation",
            "name": "Proteggere chi ama",
            "description": (
                "Vuole diventare abbastanza forte da poter "
                "proteggere le persone importanti."
            ),
            "strength": 83,
            "stability": "strong",
            "origin": "relationship",
            "reason": (
                "È legato profondamente alle persone "
                "a cui vuole bene."
            )
        },

        {
            "type": "attachment",
            "name": "Legame profondo",
            "description": (
                "Quando si affeziona a qualcuno tende a "
                "creare legami molto profondi."
            ),
            "strength": 73,
            "stability": "strong",
            "origin": "initial",
            "reason": (
                "Ha una personalità fortemente orientata "
                "ai legami personali."
            )
        },

    ]

    for psychology_data in psychology:

        psychology_id = create_character_psychology(
            character_id=character_id,
            **psychology_data
        )

        print(
            f"  Psicologia: "
            f"{psychology_data['name']} "
            f"(ID {psychology_id})"
        )

    # -----------------------------------------------------
    # CLASSE
    # -----------------------------------------------------

    print("\n[6/7] Creazione classe...")

    class_data = find_class("Investigatore")

    if class_data is None:

        class_id = create_class(
            name="Investigatore",
            description=(
                "Una classe specializzata nell'osservazione, "
                "nell'analisi e nella raccolta di informazioni."
            ),
            category="general"
        )

    else:

        class_id = class_data["id"]

    character_class_id = add_character_class(
        character_id=character_id,
        class_id=class_id,
        level=2,
        experience=150,
        is_primary=True
    )

    print(
        f"  Classe: Investigatore "
        f"(ID {character_class_id})"
    )

    # -----------------------------------------------------
    # MEMORIE
    # -----------------------------------------------------

    print("\n[7/7] Creazione memorie...")

    memories = [

        {
            "content": (
                "Da bambino passava molto tempo osservando "
                "le persone nella piazza della città."
            ),
            "memory_type": "experience",
            "importance": 4,
            "is_secret": False
        },

        {
            "content": (
                "Una persona a lui molto vicina gli insegnò "
                "che mantenere una promessa è più importante "
                "che ottenere un vantaggio personale."
            ),
            "memory_type": "knowledge",
            "importance": 8,
            "is_secret": False
        },

        {
            "content": (
                "Ha assistito a un evento che non ha mai "
                "raccontato a nessuno."
            ),
            "memory_type": "event",
            "importance": 9,
            "is_secret": True
        },

        {
            "content": (
                "Conosce una scorciatoia attraverso una parte "
                "poco frequentata della città."
            ),
            "memory_type": "place",
            "importance": 5,
            "is_secret": False
        },

        {
            "content": (
                "Sa riconoscere quando una persona sta "
                "cercando di nascondere qualcosa."
            ),
            "memory_type": "knowledge",
            "importance": 7,
            "is_secret": False
        },

    ]

    for memory in memories:

        memory_id = create_memory(
            character_id=character_id,
            **memory
        )

        print(
            f"  Memoria creata: "
            f"ID {memory_id}"
        )

    # -----------------------------------------------------
    # RISULTATO
    # -----------------------------------------------------

    print("\n" + "=" * 60)
    print("PERSONAGGIO COMPLETATO")
    print("=" * 60)

    print(f"\nID: {character_id}")
    print(f"Nome: {CHARACTER_NAME}")

    return character_id


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    character_id = create_complete_character()

    print("\n")
    print("=" * 60)
    print("TEST TERMINATO")
    print("=" * 60)
    print(
        f"Personaggio creato con ID: {character_id}"
    )