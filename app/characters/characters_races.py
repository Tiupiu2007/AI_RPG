# app/characters/characters_races.py

from dataclasses import dataclass

# =========================================================
# RACE
# =========================================================

@dataclass
class CharacterRace:

    id: str
    name: str
    description: str

    average_height: float = 0.0
    average_weight: float = 0.0

    lifespan: int = 0

    rarity: float = 1.0

    def __post_init__(self):

        self.validate()

    # =====================================================
    # VALIDAZIONE
    # =====================================================

    def validate(self):

        if not isinstance(self.id, str):

            raise TypeError(
                "L'id della razza deve essere una stringa."
            )

        if not self.id.strip():

            raise ValueError(
                "L'id della razza non può essere vuoto."
            )

        if not isinstance(self.name, str):

            raise TypeError(
                "Il nome della razza deve essere una stringa."
            )

        if not self.name.strip():

            raise ValueError(
                "Il nome della razza non può essere vuoto."
            )

        if not isinstance(self.description, str):

            raise TypeError(
                "La descrizione della razza deve essere una stringa."
            )

        if not self.description.strip():

            raise ValueError(
                "La descrizione della razza non può essere vuota."
            )

        if not isinstance(
            self.average_height,
            (int, float)
        ):

            raise TypeError(
                "L'altezza media deve essere un numero."
            )

        if not isinstance(
            self.average_weight,
            (int, float)
        ):

            raise TypeError(
                "Il peso medio deve essere un numero."
            )

        if not isinstance(
            self.lifespan,
            int
        ):

            raise TypeError(
                "La durata della vita deve essere un intero."
            )

        if not isinstance(
            self.rarity,
            (int, float)
        ):

            raise TypeError(
                "La rarità deve essere un numero."
            )

        if self.average_height < 0:

            raise ValueError(
                "L'altezza media non può essere negativa."
            )

        if self.average_weight < 0:

            raise ValueError(
                "Il peso medio non può essere negativo."
            )

        if self.lifespan < 0:

            raise ValueError(
                "La durata della vita non può essere negativa."
            )

        if not 0.0 <= self.rarity <= 1.0:

            raise ValueError(
                "La rarità deve essere compresa tra 0.0 e 1.0."
            )

        self.id = self.id.strip()
        self.name = self.name.strip()
        self.description = self.description.strip()


# =========================================================
# RAZZE DEL MONDO
# =========================================================
#
# Queste sono le razze ufficialmente conosciute dal gioco.
#
# L'IA NON può inventare una razza.
#
# Quando viene creato un personaggio:
#
# 1. Il sistema sceglie una razza da questa lista.
# 2. L'IA riceve la razza scelta.
# 3. L'IA genera l'identità coerente con quella razza.
#
# =========================================================

RACES = [

    CharacterRace(
        id="human",
        name="Umano",
        description=(
            "Una razza estremamente adattabile e diffusa. "
            "Gli umani possiedono una grande varietà di culture, "
            "tradizioni e caratteristiche fisiche."
        ),
        average_height=175.0,
        average_weight=75.0,
        lifespan=80,
        rarity=1.0,
    ),

    CharacterRace(
        id="elf",
        name="Elfo",
        description=(
            "Una razza longeva caratterizzata da una grande "
            "varietà di culture e tradizioni. Gli elfi possono "
            "essere associati alla natura, alla magia o a società "
            "completamente diverse tra loro."
        ),
        average_height=178.0,
        average_weight=65.0,
        lifespan=500,
        rarity=0.5,
    ),

    CharacterRace(
        id="dwarf",
        name="Nano",
        description=(
            "Una razza robusta e resistente, tradizionalmente "
            "legata alla vita sotterranea, alla lavorazione dei "
            "metalli e alla costruzione."
        ),
        average_height=135.0,
        average_weight=80.0,
        lifespan=250,
        rarity=0.5,
    ),

    CharacterRace(
        id="orc",
        name="Orco",
        description=(
            "Una razza fisicamente possente. Le società orchesche "
            "possono essere tribali, nomadi, guerriere, pacifiche "
            "o organizzate secondo culture completamente diverse."
        ),
        average_height=195.0,
        average_weight=105.0,
        lifespan=70,
        rarity=0.4,
    ),

    CharacterRace(
        id="demon",
        name="Demone",
        description=(
            "Una razza associata a popolazioni e culture demoniache. "
            "L'aspetto può variare considerevolmente: alcuni "
            "individui possono apparire quasi umanoidi mentre altri "
            "possono presentare caratteristiche molto più evidenti."
        ),
        average_height=180.0,
        average_weight=75.0,
        lifespan=300,
        rarity=0.2,
    ),

    CharacterRace(
        id="dragonborn",
        name="Draconide",
        description=(
            "Una razza umanoide caratterizzata da tratti draconici. "
            "Gli individui possono presentare scaglie, corna, "
            "artigli, denti particolari e altre caratteristiche "
            "tipiche della loro discendenza."
        ),
        average_height=190.0,
        average_weight=100.0,
        lifespan=150,
        rarity=0.2,
    ),

    CharacterRace(
        id="half_elf",
        name="Mezzelfo",
        description=(
            "Una razza nata dall'unione di caratteristiche umane "
            "ed elfiche. L'aspetto può variare notevolmente da "
            "individuo a individuo."
        ),
        average_height=176.0,
        average_weight=70.0,
        lifespan=180,
        rarity=0.6,
    ),

]


# =========================================================
# RICERCA RAZZA
# =========================================================

def get_race(
    name: str
) -> CharacterRace | None:

    name = name.strip()

    for race in RACES:

        if race.name.lower() == name.lower():

            return race

    return None


# =========================================================
# RICERCA TRAMITE ID
# =========================================================

def get_race_by_id(
    race_id: str
) -> CharacterRace | None:

    race_id = race_id.strip().lower()

    for race in RACES:

        if race.id.lower() == race_id:

            return race

    return None


# =========================================================
# TUTTE LE RAZZE
# =========================================================

def get_available_races() -> list[CharacterRace]:

    return list(RACES)


# =========================================================
# NOMI DELLE RAZZE
# =========================================================

def get_available_race_names() -> list[str]:

    return [
        race.name
        for race in RACES
    ]


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("RAZZE DISPONIBILI")
    print("=" * 60)

    for race in get_available_races():

        print()
        print(f"ID:       {race.id}")
        print(f"Nome:     {race.name}")
        print(f"Altezza:  {race.average_height} cm")
        print(f"Peso:     {race.average_weight} kg")
        print(f"Vita:     {race.lifespan} anni")
        print(f"Rarità:   {race.rarity}")

    print()
    print("=" * 60)

