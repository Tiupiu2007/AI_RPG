import json

from app.ai_provider import ask_ollama
from app.characters.characters_identity import CharacterIdentity, validate_identity
from app.characters.characters_races import get_available_race_names


SYSTEM_PROMPT = """
Sei il generatore di personaggi di un RPG.

Riceverai una breve descrizione scritta dall'utente oppure generata durante la storia.
Devi trasformarla in un personaggio completo, mantenendo come priorità assoluta le
informazioni esplicite della descrizione.

La razza deve appartenere ESCLUSIVAMENTE al catalogo ufficiale fornito dal sistema.
Se la descrizione indica una razza, usa quella esatta. Se non la indica, scegli la
razza ufficiale più coerente.

Non inventare razze.
Non cambiare un'età esplicitamente indicata.
Non contraddire caratteristiche esplicite della descrizione.
Completa soltanto le informazioni mancanti.

Restituisci esclusivamente JSON valido, senza Markdown e senza testo extra.
""".strip()


REQUIRED_FIELDS = {
    "name", "surname", "nickname", "age", "birth_date", "sex", "race",
    "physical_description", "appearance",
}


def generate_character_from_description(description: str) -> CharacterIdentity:
    description = str(description or "").strip()
    if not description:
        raise ValueError("La descrizione del personaggio non può essere vuota.")

    races = get_available_race_names()
    if not races:
        raise ValueError("Non sono presenti razze disponibili.")

    prompt = f"""
DESCRIZIONE DI PARTENZA:
{description}

RAZZE UFFICIALI DISPONIBILI:
{json.dumps(races, ensure_ascii=False)}

Trasforma la descrizione in una singola identità completa.
Se un'informazione non è presente, completala in modo plausibile e coerente.
La razza deve essere una delle razze ufficiali sopra elencate.

Struttura obbligatoria:
{{
  "name": "string",
  "surname": "string",
  "nickname": "string",
  "age": 0,
  "birth_date": "DD-MM-YYYY",
  "sex": "string",
  "race": "string",
  "physical_description": "string",
  "appearance": "string"
}}
""".strip()

    response = ask_ollama(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError("L'AI non ha restituito un'identità valida.") from error

    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(
            "Campi mancanti nell'identità generata: " + ", ".join(sorted(missing))
        )

    validate_identity(data)

    race = str(data["race"]).strip()
    if race.lower() not in {name.lower() for name in races}:
        raise ValueError(f"L'AI ha inventato una razza non disponibile: {race}")

    official_race = next(name for name in races if name.lower() == race.lower())

    return CharacterIdentity(
        name=str(data["name"]).strip(),
        surname=str(data["surname"]).strip(),
        nickname=str(data["nickname"]).strip(),
        age=int(data["age"]),
        birth_date=str(data["birth_date"]).strip(),
        sex=str(data["sex"]).strip(),
        race=official_race,
        physical_description=str(data["physical_description"]).strip(),
        appearance=str(data["appearance"]).strip(),
    )
