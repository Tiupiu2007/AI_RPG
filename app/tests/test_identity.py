from app.characters.characters_identity import generate_identity


def main():

    print("=" * 60)
    print("TEST GENERAZIONE IDENTITÀ")
    print("=" * 60)

    identity = generate_identity()

    print("\nIDENTITÀ GENERATA")
    print("-" * 60)

    print(f"Nome:            {identity.name}")
    print(f"Cognome:         {identity.surname}")
    print(f"Soprannome:      {identity.nickname}")
    print(f"Età:              {identity.age}")
    print(f"Data di nascita: {identity.birth_date}")
    print(f"Sesso:            {identity.sex}")
    print(f"Razza:            {identity.race}")

    print("\nDescrizione fisica:")
    print(identity.physical_description)

    print("\nAspetto:")
    print(identity.appearance)

    print("\n" + "=" * 60)
    print("TEST COMPLETATO")
    print("=" * 60)


if __name__ == "__main__":
    main()