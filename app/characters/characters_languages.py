# app/characters/characters_languages.py

from dataclasses import dataclass


# =========================================================
# WORLD LANGUAGE
# =========================================================
#
# Rappresenta una lingua esistente nel mondo.
#
# Questi dati sono STATICI.
#
# L'IA NON può creare nuove lingue.
#
# =========================================================

@dataclass
class WorldLanguage:

    id: str
    name: str

    # Quanto è diffusa nel mondo.
    # 0.0 = quasi sconosciuta
    # 1.0 = praticamente universale
    prevalence: float = 0.5

    # Difficoltà generale della lingua.
    # 0.0 = molto semplice
    # 1.0 = estremamente difficile
    difficulty: float = 0.5

    def __post_init__(self):

        self.validate()

    # =====================================================
    # VALIDAZIONE
    # =====================================================

    def validate(self):

        if not isinstance(
            self.id,
            str
        ):

            raise TypeError(
                "L'id della lingua deve essere una stringa."
            )

        if not self.id.strip():

            raise ValueError(
                "L'id della lingua non può essere vuoto."
            )

        if not isinstance(
            self.name,
            str
        ):

            raise TypeError(
                "Il nome della lingua deve essere una stringa."
            )

        if not self.name.strip():

            raise ValueError(
                "Il nome della lingua non può essere vuoto."
            )

        if not isinstance(
            self.prevalence,
            (int, float)
        ):

            raise TypeError(
                "La diffusione della lingua deve essere un numero."
            )

        if not isinstance(
            self.difficulty,
            (int, float)
        ):

            raise TypeError(
                "La difficoltà della lingua deve essere un numero."
            )

        if not 0.0 <= self.prevalence <= 1.0:

            raise ValueError(
                "La diffusione deve essere compresa "
                "tra 0.0 e 1.0."
            )

        if not 0.0 <= self.difficulty <= 1.0:

            raise ValueError(
                "La difficoltà deve essere compresa "
                "tra 0.0 e 1.0."
            )

        self.id = self.id.strip()
        self.name = self.name.strip()


# =========================================================
# CHARACTER LANGUAGE
# =========================================================
#
# Rappresenta una lingua conosciuta da UN PERSONAGGIO.
#
# La lingua può essere conosciuta a livelli differenti.
#
# 0.0 = completamente sconosciuta
# 1.0 = conoscenza perfetta
#
# =========================================================

@dataclass
class CharacterLanguage:

    language_id: str
    name: str

    # -----------------------------------------------------
    # COMPRENSIONE
    # -----------------------------------------------------
    #
    # Quanto il personaggio comprende quando ascolta
    # qualcuno parlare questa lingua.
    #
    comprehension: float = 1.0

    # -----------------------------------------------------
    # PARLATO
    # -----------------------------------------------------
    #
    # Quanto il personaggio riesce a parlare la lingua.
    #
    speaking: float = 1.0

    # -----------------------------------------------------
    # SCRITTURA
    # -----------------------------------------------------
    #
    # Quanto il personaggio sa leggere e scrivere
    # questa lingua.
    #
    writing: float = 1.0

    def __post_init__(self):

        self.validate()

    # =====================================================
    # VALIDAZIONE
    # =====================================================

    def validate(self):

        if not isinstance(
            self.language_id,
            str
        ):

            raise TypeError(
                "L'id della lingua deve essere una stringa."
            )

        if not self.language_id.strip():

            raise ValueError(
                "L'id della lingua non può essere vuoto."
            )

        if not isinstance(
            self.name,
            str
        ):

            raise TypeError(
                "Il nome della lingua deve essere una stringa."
            )

        if not self.name.strip():

            raise ValueError(
                "Il nome della lingua non può essere vuoto."
            )

        for field_name in (
            "comprehension",
            "speaking",
            "writing",
        ):

            value = getattr(
                self,
                field_name
            )

            if not isinstance(
                value,
                (int, float)
            ):

                raise TypeError(
                    f"{field_name} deve essere un numero."
                )

            if not 0.0 <= value <= 1.0:

                raise ValueError(
                    f"{field_name} deve essere compreso "
                    "tra 0.0 e 1.0."
                )

        self.language_id = (
            self.language_id
            .strip()
        )

        self.name = (
            self.name
            .strip()
        )

    # =====================================================
    # LIVELLO COMPRENSIONE
    # =====================================================

    def comprehension_level(self) -> str:

        if self.comprehension <= 0.0:
            return "sconosciuta"

        if self.comprehension < 0.15:
            return "quasi nulla"

        if self.comprehension < 0.35:
            return "molto bassa"

        if self.comprehension < 0.55:
            return "parziale"

        if self.comprehension < 0.75:
            return "buona"

        if self.comprehension < 0.95:
            return "molto buona"

        return "fluente"

    # =====================================================
    # APPRENDIMENTO
    # =====================================================

    def learn(
        self,
        amount: float
    ):

        if not isinstance(
            amount,
            (int, float)
        ):

            raise TypeError(
                "La quantità di apprendimento "
                "deve essere un numero."
            )

        if amount < 0:

            raise ValueError(
                "La quantità di apprendimento "
                "non può essere negativa."
            )

        self.comprehension = min(
            1.0,
            self.comprehension + amount
        )

        self.speaking = min(
            1.0,
            self.speaking + amount * 0.7
        )

        self.writing = min(
            1.0,
            self.writing + amount * 0.4
        )


# =========================================================
# LINGUE DEL MONDO
# =========================================================
#
# Elenco ufficiale.
#
# L'IA NON può crearne di nuove.
#
# =========================================================

LANGUAGES = [

    WorldLanguage(
        id="common",
        name="Comune",
        prevalence=1.0,
        difficulty=0.1,
    ),

    WorldLanguage(
        id="elvish",
        name="Elfico",
        prevalence=0.6,
        difficulty=0.45,
    ),

    WorldLanguage(
        id="dwarvish",
        name="Nanico",
        prevalence=0.5,
        difficulty=0.5,
    ),

    WorldLanguage(
        id="orcish",
        name="Orchesco",
        prevalence=0.45,
        difficulty=0.4,
    ),

    WorldLanguage(
        id="draconic",
        name="Draconico",
        prevalence=0.2,
        difficulty=0.75,
    ),

    WorldLanguage(
        id="demonic",
        name="Demoniaco",
        prevalence=0.2,
        difficulty=0.8,
    ),

    WorldLanguage(
        id="celestial",
        name="Celestiale",
        prevalence=0.15,
        difficulty=0.9,
    ),

    WorldLanguage(
        id="ancient",
        name="Antico",
        prevalence=0.1,
        difficulty=0.95,
    ),

    WorldLanguage(
        id="arcane",
        name="Magico",
        prevalence=0.2,
        difficulty=0.9,
    ),

    WorldLanguage(
        id="goblin",
        name="Goblin",
        prevalence=0.4,
        difficulty=0.35,
    ),

    WorldLanguage(
        id="giant",
        name="Gigante",
        prevalence=0.25,
        difficulty=0.65,
    ),

    WorldLanguage(
        id="abyssal",
        name="Abissale",
        prevalence=0.15,
        difficulty=0.9,
    ),

    WorldLanguage(
        id="infernal",
        name="Infernale",
        prevalence=0.2,
        difficulty=0.85,
    ),

    WorldLanguage(
        id="sylvan",
        name="Silvano",
        prevalence=0.25,
        difficulty=0.7,
    ),

    WorldLanguage(
        id="maritime",
        name="Marino",
        prevalence=0.3,
        difficulty=0.55,
    ),

    WorldLanguage(
        id="runic",
        name="Runico",
        prevalence=0.1,
        difficulty=0.85,
    ),

]


# =========================================================
# LINGUE PRINCIPALI PER RAZZA
# =========================================================

RACE_DEFAULT_LANGUAGES = {

    "Umano": [
        "Comune",
    ],

    "Elfo": [
        "Elfico",
        "Comune",
    ],

    "Nano": [
        "Nanico",
        "Comune",
    ],

    "Orco": [
        "Orchesco",
        "Comune",
    ],

    "Goblin": [
        "Goblin",
        "Comune",
    ],

    "Gigante": [
        "Gigante",
        "Comune",
    ],

    "Demone": [
        "Demoniaco",
        "Comune",
    ],

    "Draconide": [
        "Draconico",
        "Comune",
    ],

    "Mezzelfo": [
        "Comune",
        "Elfico",
    ],

}


# =========================================================
# RICERCA LINGUA TRAMITE ID
# =========================================================

def get_language_by_id(
    language_id: str
) -> WorldLanguage | None:

    if not isinstance(
        language_id,
        str
    ):

        return None

    language_id = (
        language_id
        .strip()
        .lower()
    )

    for language in LANGUAGES:

        if language.id.lower() == language_id:

            return language

    return None


# =========================================================
# RICERCA LINGUA TRAMITE NOME
# =========================================================

def get_language(
    language_name: str
) -> WorldLanguage | None:

    if not isinstance(
        language_name,
        str
    ):

        return None

    language_name = (
        language_name
        .strip()
        .lower()
    )

    for language in LANGUAGES:

        if language.name.lower() == language_name:

            return language

    return None


# =========================================================
# CONTROLLO LINGUA
# =========================================================

def is_valid_language(
    language_name: str
) -> bool:

    return (
        get_language(language_name)
        is not None
    )


# =========================================================
# CREA LINGUA PER UN PERSONAGGIO
# =========================================================

def create_character_language(
    language_name: str,
    comprehension: float = 1.0,
    speaking: float = 1.0,
    writing: float = 1.0,
) -> CharacterLanguage:

    language = get_language(
        language_name
    )

    if language is None:

        raise ValueError(
            f"Lingua non disponibile: "
            f"{language_name}"
        )

    return CharacterLanguage(

        language_id=language.id,

        name=language.name,

        comprehension=comprehension,

        speaking=speaking,

        writing=writing,

    )


# =========================================================
# LINGUE PRINCIPALI DELLA RAZZA
# =========================================================

def get_race_languages(
    race: str
) -> list[CharacterLanguage]:

    if not isinstance(
        race,
        str
    ):

        raise TypeError(
            "La razza deve essere una stringa."
        )

    race = race.strip()

    language_names = (
        RACE_DEFAULT_LANGUAGES.get(
            race,
            ["Comune"]
        )
    )

    languages = []

    for language_name in language_names:

        language = create_character_language(
            language_name=language_name,
            comprehension=1.0,
            speaking=1.0,
            writing=1.0,
        )

        languages.append(
            language
        )

    return languages


# =========================================================
# TUTTE LE LINGUE DISPONIBILI
# =========================================================

def get_available_languages() -> list[WorldLanguage]:

    return [

        WorldLanguage(
            id=language.id,
            name=language.name,
            prevalence=language.prevalence,
            difficulty=language.difficulty,
        )

        for language in LANGUAGES

    ]


# =========================================================
# NOMI DELLE LINGUE
# =========================================================

def get_available_language_names() -> list[str]:

    return [

        language.name

        for language in LANGUAGES

    ]


# =========================================================
# ID DELLE LINGUE
# =========================================================

def get_available_language_ids() -> list[str]:

    return [

        language.id

        for language in LANGUAGES

    ]


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("TEST SISTEMA LINGUE")
    print("=" * 60)

    print()
    print("Lingue disponibili:")

    for language in get_available_languages():

        print(
            f"- {language.id}: "
            f"{language.name} "
            f"(diffusione={language.prevalence}, "
            f"difficoltà={language.difficulty})"
        )

    print()
    print("Lingue predefinite del Mezzelfo:")

    for language in get_race_languages(
        "Mezzelfo"
    ):

        print(
            f"- {language.name}: "
            f"comprensione={language.comprehension}, "
            f"parlato={language.speaking}, "
            f"scrittura={language.writing}"
        )

    print()
    print("Test apprendimento:")

    elfico = create_character_language(
        "Elfico",
        comprehension=0.10,
        speaking=0.05,
        writing=0.0,
    )

    print(
        "Prima:",
        elfico.comprehension_level()
    )

    elfico.learn(
        0.20
    )

    print(
        "Dopo:",
        elfico.comprehension_level()
    )

    print(
        "Comprensione:",
        round(
            elfico.comprehension,
            2
        )
    )

    print(
        "Parlato:",
        round(
            elfico.speaking,
            2
        )
    )

    print(
        "Scrittura:",
        round(
            elfico.writing,
            2
        )
    )

    print()
    print("Controllo lingue:")

    print(
        "Elfico:",
        is_valid_language("Elfico")
    )

    print(
        "LinguaInventata:",
        is_valid_language("LinguaInventata")
    )

    print()
    print("=" * 60)
    print("TEST COMPLETATO")
    print("=" * 60)

