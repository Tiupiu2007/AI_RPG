# app/characters/characters_identity.py

import json
from dataclasses import dataclass

from app.ai_provider import ask_ollama


# =========================================================
# IDENTITY
# =========================================================

@dataclass
class CharacterIdentity:

    name: str
    surname: str
    nickname: str

    age: int
    birth_date: str

    sex: str
    race: str

    physical_description: str
    appearance: str


# =========================================================
# PROMPT
# =========================================================

SYSTEM_PROMPT = """
Sei un generatore di identità per personaggi di un RPG.

Devi generare una singola identità completa per una razza
che ti viene fornita dal sistema.

La razza NON deve essere scelta da te.

Devi utilizzare ESATTAMENTE la razza fornita.

Il personaggio può essere:

- giovane;
- adulto;
- anziano;
- comune;
- particolare;
- realistico;
- fantasy.

Non deve essere necessariamente speciale.

Genera solamente i dati richiesti.

Devi restituire ESCLUSIVAMENTE JSON valido.

NON usare Markdown.
NON usare ```json.
NON aggiungere spiegazioni.
NON aggiungere testo prima o dopo il JSON.

La struttura obbligatoria è:

{
    "name": "string",
    "surname": "string",
    "nickname": "string",
    "age": 0,
    "birth_date": "DD-MM-YYYY",
    "sex": "string",
    "race": "string",
    "physical_description": "string",
    "appearance": "string"
}

=========================================================

name:

Nome proprio del personaggio.

Deve essere coerente con la razza fornita
e con la relativa cultura.

=========================================================

surname:

Cognome del personaggio.

Può essere assente solamente se la razza o la cultura
non utilizza cognomi.

In quel caso usa:

""

=========================================================

nickname:

Soprannome del personaggio.

Può derivare dal nome, dall'aspetto, dalla professione,
dalla reputazione o dalla sua storia.

Non è obbligatorio.

Se non possiede un soprannome, usa:

""

=========================================================

age:

Età del personaggio espressa in anni.

Deve essere un numero intero.

L'età deve essere plausibile per la razza fornita.

=========================================================

birth_date:

Data di nascita.

DEVE essere SEMPRE nel formato europeo:

DD-MM-YYYY

Esempio:

17-06-1995

NON usare:

1995-06-17

NON usare:

06-17-1995

La data deve essere compatibile con l'età.

=========================================================

sex:

Sesso del personaggio.

=========================================================

race:

Razza del personaggio.

IMPORTANTE:

Devi utilizzare ESATTAMENTE la razza fornita
dal sistema.

NON modificarla.

NON inventare una razza alternativa.

NON creare una nuova razza.

=========================================================

physical_description:

Descrizione generale della costituzione fisica.

Deve essere abbastanza dettagliata.

Può descrivere:

- corporatura;
- struttura del corpo;
- muscolatura;
- postura;
- proporzioni;
- lineamenti del viso;
- mani;
- gambe;
- caratteristiche fisiche della razza;
- cicatrici;
- deformità;
- caratteristiche particolari.

La descrizione deve sembrare quella di una persona reale.

Deve essere coerente con la razza fornita.

=========================================================

appearance:

Descrizione dell'aspetto esteriore.

Deve essere abbastanza dettagliata.

Può includere:

- capelli;
- occhi;
- pelle;
- volto;
- barba;
- acconciatura;
- abbigliamento abituale;
- accessori;
- gioielli;
- segni distintivi;
- cicatrici visibili;
- tatuaggi;
- modo abituale di presentarsi.

Non deve essere una semplice ripetizione della
physical_description.

Deve essere coerente con la razza.

=========================================================

# COERENZA

Tutti i dati devono appartenere alla stessa persona.

La razza deve essere esattamente quella fornita.

Il nome deve essere plausibile per la razza.

L'età deve essere compatibile con la razza.

La data di nascita deve essere compatibile con l'età.

L'aspetto deve essere coerente con la razza.

La descrizione fisica e l'aspetto devono descrivere
la stessa persona.

Non rendere il personaggio necessariamente speciale.

Non aggiungere:

- poteri;
- abilità;
- statistiche;
- equipaggiamento;
- lingue;
- psicologia;
- personalità;
- relazioni;
- informazioni non richieste.

""".strip()


# =========================================================
# VALIDAZIONE
# =========================================================

def validate_identity(data: dict) -> None:

    required_fields = {
        "name",
        "surname",
        "nickname",
        "age",
        "birth_date",
        "sex",
        "race",
        "physical_description",
        "appearance",
    }

    missing_fields = required_fields - data.keys()

    if missing_fields:

        raise ValueError(
            f"Campi mancanti nell'identità: "
            f"{', '.join(sorted(missing_fields))}"
        )

    # -----------------------------------------------------
    # STRINGHE
    # -----------------------------------------------------

    string_fields = (
        "name",
        "surname",
        "nickname",
        "birth_date",
        "sex",
        "race",
        "physical_description",
        "appearance",
    )

    for field_name in string_fields:

        value = data[field_name]

        if not isinstance(value, str):

            raise TypeError(
                f"{field_name} deve essere una stringa."
            )

    if not data["name"].strip():

        raise ValueError(
            "Il nome non può essere vuoto."
        )

    if not data["sex"].strip():

        raise ValueError(
            "Il sesso non può essere vuoto."
        )

    if not data["race"].strip():

        raise ValueError(
            "La razza non può essere vuota."
        )

    if not data["physical_description"].strip():

        raise ValueError(
            "La descrizione fisica non può essere vuota."
        )

    if not data["appearance"].strip():

        raise ValueError(
            "L'aspetto non può essere vuoto."
        )

    # -----------------------------------------------------
    # ETÀ
    # -----------------------------------------------------

    if not isinstance(data["age"], int):

        raise TypeError(
            "L'età deve essere un intero."
        )

    if not 0 <= data["age"] <= 999:

        raise ValueError(
            "L'età deve essere compresa tra 0 e 999."
        )

    # -----------------------------------------------------
    # DATA DI NASCITA
    # -----------------------------------------------------

    birth_date = data["birth_date"]

    parts = birth_date.split("-")

    if len(parts) != 3:

        raise ValueError(
            "La data di nascita deve avere formato "
            "DD-MM-YYYY."
        )

    if not all(
        part.isdigit()
        for part in parts
    ):

        raise ValueError(
            "La data di nascita non è valida."
        )

    day, month, year = map(
        int,
        parts
    )

    if not 1 <= day <= 31:

        raise ValueError(
            "Giorno di nascita non valido."
        )

    if not 1 <= month <= 12:

        raise ValueError(
            "Mese di nascita non valido."
        )

    if year < 1:

        raise ValueError(
            "Anno di nascita non valido."
        )


# =========================================================
# GENERAZIONE
# =========================================================

def generate_identity(
    race: str
) -> CharacterIdentity:

    race = race.strip()

    if not race:

        raise ValueError(
            "La razza deve essere specificata."
        )

    # -----------------------------------------------------
    # PROMPT UTENTE
    # -----------------------------------------------------

    user_prompt = f"""
Genera una nuova identità casuale per un personaggio.

La razza del personaggio è:

{race}

Devi utilizzare esattamente questa razza.

Non scegliere una razza diversa.

Non inventare nuove razze.

Crea semplicemente una persona completa e plausibile
appartenente a questa razza.

Assicurati che:

- nome;
- cognome;
- età;
- data di nascita;
- sesso;
- descrizione fisica;
- aspetto

siano coerenti tra loro e con la razza.

Genera esclusivamente i campi richiesti.
""".strip()

    # -----------------------------------------------------
    # AI
    # -----------------------------------------------------

    response = ask_ollama(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # -----------------------------------------------------
    # JSON
    # -----------------------------------------------------

    try:

        data = json.loads(response)

    except json.JSONDecodeError as error:

        print("\nRisposta ricevuta dall'AI:")
        print(response)

        raise ValueError(
            "L'AI non ha restituito JSON valido."
        ) from error

    # -----------------------------------------------------
    # VALIDAZIONE
    # -----------------------------------------------------

    validate_identity(data)

    # -----------------------------------------------------
    # CONTROLLO RAZZA
    # -----------------------------------------------------

    generated_race = data["race"].strip()

    if generated_race != race:

        raise ValueError(
            "L'AI ha restituito una razza diversa "
            "da quella richiesta. "
            f"Richiesta: {race} | "
            f"Ricevuta: {generated_race}"
        )

    # -----------------------------------------------------
    # CREAZIONE
    # -----------------------------------------------------

    return CharacterIdentity(

        name=data["name"].strip(),

        surname=data["surname"].strip(),

        nickname=data["nickname"].strip(),

        age=data["age"],

        birth_date=data["birth_date"].strip(),

        sex=data["sex"].strip(),

        race=generated_race,

        physical_description=data[
            "physical_description"
        ].strip(),

        appearance=data[
            "appearance"
        ].strip(),
    )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("GENERAZIONE IDENTITÀ")
    print("=" * 60)

    # TEMPORANEO:
    # successivamente la razza arriverà
    # direttamente dal sistema delle razze.

    race = "Mezzelfo"

    print()
    print(f"Razza assegnata dal sistema: {race}")
    print()

    identity = generate_identity(race)

    print("=" * 60)
    print("IDENTITÀ GENERATA")
    print("=" * 60)

    print()

    print(f"Nome:            {identity.name}")
    print(f"Cognome:         {identity.surname}")
    print(f"Soprannome:      {identity.nickname}")

    print(f"Età:             {identity.age}")
    print(f"Data di nascita: {identity.birth_date}")

    print(f"Sesso:           {identity.sex}")
    print(f"Razza:           {identity.race}")

    print()

    print("Descrizione fisica:")
    print(identity.physical_description)

    print()

    print("Aspetto:")
    print(identity.appearance)

    print()

    print("=" * 60)
    print("IDENTITÀ GENERATA CORRETTAMENTE")
    print("=" * 60)