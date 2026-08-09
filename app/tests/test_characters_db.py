from app.characters.characters_identity import generate_identity

from app.database.characters_db import (
    init_database,
    save_identity,
    get_identity,
    update_identity,
    delete_character,
)


def main():

    print("=" * 60)
    print("TEST DATABASE PERSONAGGI")
    print("=" * 60)

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    print("\nInizializzazione database...")

    init_database()

    print("Database pronto.")

    # -----------------------------------------------------
    # GENERAZIONE
    # -----------------------------------------------------

    print("\nGenerazione identità...")

    identity = generate_identity()

    print(
        f"{identity.name} "
        f"{identity.surname}"
    )

    # -----------------------------------------------------
    # SALVATAGGIO
    # -----------------------------------------------------

    print("\nSalvataggio...")

    character_id = save_identity(
        identity
    )

    print(
        f"Personaggio salvato con ID: "
        f"{character_id}"
    )

    # -----------------------------------------------------
    # LETTURA
    # -----------------------------------------------------

    print("\nLettura dal database...")

    loaded_identity = get_identity(
        character_id
    )

    if loaded_identity is None:

        raise RuntimeError(
            "Il personaggio non è stato trovato."
        )

    print(
        f"Nome: "
        f"{loaded_identity.name}"
    )

    print(
        f"Cognome: "
        f"{loaded_identity.surname}"
    )

    print(
        f"Razza: "
        f"{loaded_identity.race}"
    )

    # -----------------------------------------------------
    # AGGIORNAMENTO
    # -----------------------------------------------------

    print("\nModifica identità...")

    loaded_identity.nickname = "Test"

    update_identity(
        character_id,
        loaded_identity
    )

    updated_identity = get_identity(
        character_id
    )

    print(
        f"Nuovo soprannome: "
        f"{updated_identity.nickname}"
    )

    # -----------------------------------------------------
    # ELIMINAZIONE
    # -----------------------------------------------------

    print("\nEliminazione personaggio...")

    delete_character(
        character_id
    )

    deleted_identity = get_identity(
        character_id
    )

    if deleted_identity is not None:

        raise RuntimeError(
            "Il personaggio non è stato eliminato."
        )

    print("Personaggio eliminato.")

    print()
    print("=" * 60)
    print("TEST COMPLETATO")
    print("=" * 60)


if __name__ == "__main__":
    main()