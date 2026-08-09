import json
from dataclasses import dataclass

from app.ai_provider import ask_ollama


@dataclass
class CharacterProfile:
    mental_state: str
    emotional_stability: str
    fears: str
    desires: str
    values: str
    traumas: str
    personality_description: str
    traits: str
    strengths: str
    flaws: str
    habits: str
    social_behavior: str


SYSTEM_PROMPT = """
Sei un generatore di psicologia e personalità per un personaggio RPG.

Riceverai un'identità già definita. Devi descrivere la stessa persona.
Non cambiare nome, razza, età, sesso o aspetto.
Non inventare statistiche, abilità, poteri, equipaggiamento o relazioni.

La psicologia e la personalità devono essere coerenti con l'identità,
ma non devono trasformare automaticamente il personaggio in un eroe,
un prescelto o in qualcuno di eccezionale.

Restituisci ESCLUSIVAMENTE JSON valido, senza Markdown e senza testo extra.

Struttura obbligatoria:
{
  "mental_state": "string",
  "emotional_stability": "string",
  "fears": "string",
  "desires": "string",
  "values": "string",
  "traumas": "string",
  "personality_description": "string",
  "traits": "string",
  "strengths": "string",
  "flaws": "string",
  "habits": "string",
  "social_behavior": "string"
}
""".strip()


REQUIRED_FIELDS = {
    "mental_state",
    "emotional_stability",
    "fears",
    "desires",
    "values",
    "traumas",
    "personality_description",
    "traits",
    "strengths",
    "flaws",
    "habits",
    "social_behavior",
}


def generate_character_profile(identity: dict) -> CharacterProfile:
    if not isinstance(identity, dict):
        raise ValueError("L'identità deve essere un oggetto.")

    user_prompt = f"""
Genera psicologia e personalità per questo personaggio.

IDENTITÀ:
{json.dumps(identity, ensure_ascii=False, indent=2)}

Mantieni una personalità credibile e coerente con questa persona.
Paure, desideri, valori, traumi e abitudini devono essere compatibili
tra loro e con la sua storia implicita. I difetti devono avere conseguenze
reali sul comportamento e i pregi non devono renderlo perfetto.
""".strip()

    response = ask_ollama(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError("L'AI non ha restituito un profilo psicologico valido.") from error

    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(
            "Campi mancanti nel profilo: " + ", ".join(sorted(missing))
        )

    for field in REQUIRED_FIELDS:
        if not isinstance(data[field], str):
            raise TypeError(f"{field} deve essere una stringa.")

    return CharacterProfile(
        **{field: data[field].strip() for field in REQUIRED_FIELDS}
    )


def profile_to_dict(profile: CharacterProfile) -> dict:
    return {
        "mental_state": profile.mental_state,
        "emotional_stability": profile.emotional_stability,
        "fears": profile.fears,
        "desires": profile.desires,
        "values": profile.values,
        "traumas": profile.traumas,
        "personality_description": profile.personality_description,
        "traits": profile.traits,
        "strengths": profile.strengths,
        "flaws": profile.flaws,
        "habits": profile.habits,
        "social_behavior": profile.social_behavior,
    }
