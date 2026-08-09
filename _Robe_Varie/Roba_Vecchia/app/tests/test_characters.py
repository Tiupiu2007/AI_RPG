import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from _Robe_Varie.Roba_Vecchia.app.database import (
    initialize_database,
    reset_database
)

from _Robe_Varie.Roba_Vecchia.app.characters.character import (
    create_character,
    get_character,
    update_character,
    is_character_alive,
    set_character_alive
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_stats import (
    create_character_statistics,
    get_character_statistics,
    get_character_stat,
    set_character_stat,
    modify_character_stat,
    get_total_stat_points,
    get_all_character_stats
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_progression import (
    create_character_progression,
    get_character_progression,
    progression_to_dict,
    calculate_xp_required,
    get_level_stat_points,
    get_available_stat_points,
    update_character_progression,
    add_character_xp,
    set_character_level,
    is_max_level
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_state import (
    create_character_state,
    get_character_state,
    update_character_state,
    save_character_state,
    state_to_dict
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_classes import (
    create_class,
    get_class,
    get_all_classes,
    find_class,
    update_class,
    delete_class,
    add_character_class,
    remove_character_class,
    get_character_classes,
    get_character_class,
    set_primary_class,
    update_character_class
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_traits import (
    create_character_trait,
    get_character_trait,
    get_character_traits,
    update_character_trait,
    delete_character_trait
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_psychology import (
    create_character_psychology,
    get_character_psychology,
    get_character_psychologies,
    update_character_psychology,
    delete_character_psychology
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_memories import (
    create_memory,
    get_memory,
    get_character_memories,
    update_memory,
    delete_memory
)

from _Robe_Varie.Roba_Vecchia.app.characters.character_family import (
    create_family_relationship,
    get_family_relationship,
    get_character_family,
    update_family_relationship,
    delete_family_relationship
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run_test():

    print()
    print("=" * 60)
    print("CHARACTER SYSTEM TEST")
    print("=" * 60)

    reset_database()
    initialize_database()

    print("[1/12] Creazione personaggio...", end=" ")

    character_id = create_character(
        name="Test",
        surname="Character",
        age=20,
        sex="male",
        gender="male",
        species="human",
        description="Personaggio utilizzato per i test.",
        appearance="Capelli neri.",
        voice="Voce calma."
    )

    check(
        isinstance(character_id, int),
        "ID personaggio non valido."
    )

    character = get_character(character_id)

    check(
        character is not None,
        "Personaggio non trovato."
    )

    check(
        character["name"] == "Test",
        "Nome del personaggio errato."
    )

    check(
        character["alive"] is True,
        "Il personaggio dovrebbe essere vivo."
    )

    print("OK")

    print("[2/12] Aggiornamento personaggio...", end=" ")

    result = update_character(
        character_id,
        description="Descrizione aggiornata."
    )

    check(
        result is True,
        "Aggiornamento personaggio fallito."
    )

    character = get_character(character_id)

    check(
        character["description"] == "Descrizione aggiornata.",
        "Descrizione non aggiornata."
    )

    print("OK")

    print("[3/12] Statistiche...", end=" ")

    create_character_statistics(
        character_id,
        strength=10,
        constitution=15,
        speed=12,
        intelligence=20,
        perception=14,
        willpower=18,
        luck=5
    )

    stats = get_character_statistics(character_id)

    check(
        stats is not None,
        "Statistiche non trovate."
    )

    check(
        stats["strength"] == 10,
        "Forza errata."
    )

    check(
        get_character_stat(
            character_id,
            "intelligence"
        ) == 20,
        "Intelligenza errata."
    )

    set_character_stat(
        character_id,
        "strength",
        25
    )

    check(
        get_character_stat(
            character_id,
            "strength"
        ) == 25,
        "set_character_stat non funziona."
    )

    new_speed = modify_character_stat(
        character_id,
        "speed",
        5
    )

    check(
        new_speed == 17,
        "modify_character_stat non funziona."
    )

    all_stats = get_all_character_stats(
        character_id
    )

    check(
        len(all_stats) == 7,
        "Numero statistiche errato."
    )

    total_stats = get_total_stat_points(
        character_id
    )

    check(
        total_stats == sum(all_stats.values()),
        "Totale statistiche errato."
    )

    print("OK")

    print("[4/12] Progressione...", end=" ")

    create_character_progression(
        character_id,
        level=1,
        xp=0,
        xp_required=100
    )

    progression = get_character_progression(
        character_id
    )

    check(
        progression is not None,
        "Progressione non trovata."
    )

    progression_dict = progression_to_dict(
        progression
    )

    check(
        progression_dict["level"] == 1,
        "Livello iniziale errato."
    )

    check(
        progression_dict["xp"] == 0,
        "XP iniziale errata."
    )

    check(
        calculate_xp_required(1) == 100,
        "Calcolo XP errato."
    )

    check(
        get_level_stat_points(1) == 10,
        "Punti statistica livello errati."
    )

    check(
        get_available_stat_points(
            1,
            total_stats
        ) == 0,
        "Punti statistica disponibili errati."
    )

    update_character_progression(
        character_id,
        xp_required=100
    )

    result = add_character_xp(
        character_id,
        100
    )

    check(
        result["level"] == 2,
        "Level-up non eseguito."
    )

    progression = progression_to_dict(
        get_character_progression(character_id)
    )

    check(
        progression["level"] == 2,
        "Livello dopo XP errato."
    )

    set_character_level(
        character_id,
        5
    )

    progression = progression_to_dict(
        get_character_progression(character_id)
    )

    check(
        progression["level"] == 5,
        "set_character_level non funziona."
    )

    check(
        is_max_level(5) is False,
        "is_max_level errato."
    )

    check(
        is_max_level(999) is True,
        "is_max_level non riconosce il livello massimo."
    )

    print("OK")

    print("[5/12] Stato del personaggio...", end=" ")

    create_character_state(
        character_id,
        emotion="calmo",
        thought="Sto osservando la situazione.",
        intention="Aspettare.",
        goal="Capire cosa sta succedendo."
    )

    state = get_character_state(
        character_id
    )

    check(
        state is not None,
        "Stato non trovato."
    )

    check(
        state["emotion"] == "calmo",
        "Emozione errata."
    )

    update_character_state(
        character_id,
        emotion="preoccupato",
        thought="Qualcosa non va.",
        intention="Indagare.",
        goal="Scoprire la verità."
    )

    state = state_to_dict(
        get_character_state(character_id)
    )

    check(
        state["emotion"] == "preoccupato",
        "Stato non aggiornato."
    )

    save_character_state(
        character_id,
        emotion="arrabbiato",
        thought="Non posso ignorarlo.",
        intention="Agire.",
        goal="Proteggere gli altri."
    )

    state = state_to_dict(
        get_character_state(character_id)
    )

    check(
        state["emotion"] == "arrabbiato",
        "save_character_state non funziona."
    )

    print("OK")

    print("[6/12] Classi...", end=" ")

    class_id = create_class(
        name="Guerriero",
        description="Classe orientata al combattimento.",
        category="combat"
    )

    character_class = get_class(
        class_id
    )

    check(
        character_class is not None,
        "Classe non trovata."
    )

    check(
        character_class["name"] == "Guerriero",
        "Nome classe errato."
    )

    found_class = find_class(
        "guerriero"
    )

    check(
        found_class is not None,
        "Ricerca classe non funziona."
    )

    classes = get_all_classes()

    check(
        len(classes) >= 1,
        "Elenco classi vuoto."
    )

    update_class(
        class_id,
        description="Classe da combattimento aggiornata."
    )

    character_class = get_class(
        class_id
    )

    check(
        character_class["description"]
        == "Classe da combattimento aggiornata.",
        "Aggiornamento classe fallito."
    )

    print("OK")

    print("[7/12] Classi del personaggio...", end=" ")

    character_class_id = add_character_class(
        character_id=character_id,
        class_id=class_id,
        level=1,
        experience=0,
        is_primary=True
    )

    check(
        isinstance(character_class_id, int),
        "ID classe-personaggio non valido."
    )

    assigned_class = get_character_class(
        character_id,
        class_id
    )

    check(
        assigned_class is not None,
        "Classe non assegnata al personaggio."
    )

    check(
        assigned_class["level"] == 1,
        "Livello classe errato."
    )

    check(
        assigned_class["experience"] == 0,
        "Esperienza classe errata."
    )

    check(
        assigned_class["is_primary"] == 1,
        "La classe dovrebbe essere primaria."
    )

    assigned_classes = get_character_classes(
        character_id
    )

    check(
        len(assigned_classes) == 1,
        "Numero classi del personaggio errato."
    )

    update_character_class(
        character_id,
        class_id,
        level=5,
        experience=250
    )

    assigned_class = get_character_class(
        character_id,
        class_id
    )

    check(
        assigned_class["level"] == 5,
        "Livello classe non aggiornato."
    )

    check(
        assigned_class["experience"] == 250,
        "Esperienza classe non aggiornata."
    )

    set_primary_class(
        character_id,
        class_id
    )

    check(
        get_character_class(
            character_id,
            class_id
        )["is_primary"] == 1,
        "Classe primaria non impostata."
    )

    print("OK")

    print("[8/12] Tratti...", end=" ")

    trait_id = create_character_trait(
        character_id=character_id,
        name="Coraggioso",
        description="Affronta situazioni pericolose.",
        category="personality",
        strength=80,
        stability="strong",
        origin="initial",
        reason="Personalità naturale."
    )

    trait = get_character_trait(
        trait_id
    )

    check(
        trait is not None,
        "Tratto non trovato."
    )

    traits = get_character_traits(
        character_id
    )

    check(
        len(traits) == 1,
        "Numero tratti errato."
    )

    update_character_trait(
        trait_id,
        strength=90
    )

    trait = get_character_trait(
        trait_id
    )

    check(
        trait["strength"] == 90,
        "Aggiornamento tratto fallito."
    )

    print("OK")

    print("[9/12] Psicologia...", end=" ")

    psychology_id = create_character_psychology(
        character_id=character_id,
        type="fear",
        name="Paura dell'abbandono",
        description="Ha paura di perdere le persone importanti.",
        strength=70,
        stability="strong",
        origin="past",
        reason="Esperienze precedenti."
    )

    psychology = get_character_psychology(
        psychology_id
    )

    check(
        psychology is not None,
        "Elemento psicologico non trovato."
    )

    psychologies = get_character_psychologies(
        character_id
    )

    check(
        len(psychologies) == 1,
        "Numero elementi psicologici errato."
    )

    update_character_psychology(
        psychology_id,
        strength=75
    )

    psychology = get_character_psychology(
        psychology_id
    )

    check(
        psychology["strength"] == 75,
        "Aggiornamento psicologia fallito."
    )

    print("OK")

    print("[10/12] Memorie...", end=" ")

    memory_id = create_memory(
        character_id=character_id,
        content="Ha incontrato una persona misteriosa.",
        memory_type="event",
        importance=8,
        is_secret=False
    )

    memory = get_memory(
        memory_id
    )

    check(
        memory is not None,
        "Memoria non trovata."
    )

    memories = get_character_memories(
        character_id
    )

    check(
        len(memories) == 1,
        "Numero memorie errato."
    )

    update_memory(
        memory_id,
        content="Ha incontrato una persona misteriosa nel castello.",
        importance=9
    )

    memory = get_memory(
        memory_id
    )

    check(
        memory["importance"] == 9,
        "Aggiornamento memoria fallito."
    )

    print("OK")

    print("[11/12] Famiglia e vita/morte...", end=" ")

    second_character_id = create_character(
        name="Second",
        surname="Character",
        age=25,
        species="human"
    )

    family_id = create_family_relationship(
        character_a_id=character_id,
        character_b_id=second_character_id,
        relationship_type="brother",
        biological=True,
        confirmed=True
    )

    family = get_family_relationship(
        family_id
    )

    check(
        family is not None,
        "Relazione familiare non trovata."
    )

    family_members = get_character_family(
        character_id
    )

    check(
        len(family_members) == 1,
        "Relazione familiare non presente."
    )

    update_family_relationship(
        family_id,
        confirmed=False
    )

    family = get_family_relationship(
        family_id
    )

    check(
        family["confirmed"] == 0,
        "Aggiornamento famiglia fallito."
    )

    check(
        is_character_alive(character_id) is True,
        "Il personaggio dovrebbe essere vivo."
    )

    set_character_alive(
        character_id,
        False
    )

    check(
        is_character_alive(character_id) is False,
        "Morte del personaggio non registrata."
    )

    character = get_character(
        character_id
    )

    check(
        character is not None,
        "Il personaggio morto è stato eliminato."
    )

    set_character_alive(
        character_id,
        True
    )

    print("OK")

    print("[12/12] Controllo finale database...", end=" ")

    final_character = get_character(
        character_id
    )

    final_stats = get_character_statistics(
        character_id
    )

    final_progression = progression_to_dict(
        get_character_progression(character_id)
    )

    final_state = state_to_dict(
        get_character_state(character_id)
    )

    final_classes = get_character_classes(
        character_id
    )

    final_traits = get_character_traits(
        character_id
    )

    final_psychology = get_character_psychologies(
        character_id
    )

    final_memories = get_character_memories(
        character_id
    )

    final_family = get_character_family(
        character_id
    )

    check(
        final_character is not None,
        "Identità finale mancante."
    )

    check(
        final_stats is not None,
        "Statistiche finali mancanti."
    )

    check(
        final_progression is not None,
        "Progressione finale mancante."
    )

    check(
        final_state is not None,
        "Stato finale mancante."
    )

    check(
        len(final_classes) == 1,
        "Classi finali errate."
    )

    check(
        len(final_traits) == 1,
        "Tratti finali errati."
    )

    check(
        len(final_psychology) == 1,
        "Psicologia finale errata."
    )

    check(
        len(final_memories) == 1,
        "Memorie finali errate."
    )

    check(
        len(final_family) == 1,
        "Famiglia finale errata."
    )

    print("OK")

    print()
    print("=" * 60)
    print("TEST COMPLETATO")
    print("TUTTI I SISTEMI CHARACTERS FUNZIONANO")
    print("=" * 60)
    print()

    reset_database()


if __name__ == "__main__":

    try:
        run_test()

    except Exception as error:

        print()
        print("=" * 60)
        print("TEST FALLITO")
        print("=" * 60)
        print()
        print(type(error).__name__)
        print(error)
        print()

        raise