// =========================================================
// AI RPG - CHARACTER EDITOR
// =========================================================
//
// app.js
//
// Stato principale dell'interfaccia.
// Razze e lingue vengono caricate dal backend
// tramite API.
//
// =========================================================

// =========================================================
// STATO
// =========================================================

let character = null;

let availableRaces = [];

let availableLanguages = [];


// =========================================================
// ELEMENTI DOM
// =========================================================

const generateButton =
    document.getElementById(
        "generateButton"
    );


const newCharacterButton =
    document.getElementById(
        "newCharacterButton"
    );


const saveButton =
    document.getElementById(
        "saveButton"
    );


const overlay =
    document.getElementById(
        "generationOverlay"
    );


const progressBar =
    document.getElementById(
        "progressBar"
    );


const progressText =
    document.getElementById(
        "progressText"
    );


const generationStatus =
    document.getElementById(
        "generationStatus"
    );


const generationName =
    document.getElementById(
        "generationName"
    );


// =========================================================
// INPUT
// =========================================================

const inputs = {

    name:
        document.getElementById(
            "name"
        ),

    surname:
        document.getElementById(
            "surname"
        ),

    nickname:
        document.getElementById(
            "nickname"
        ),

    age:
        document.getElementById(
            "age"
        ),

    birthDate:
        document.getElementById(
            "birthDate"
        ),

    sex:
        document.getElementById(
            "sex"
        ),

    race:
        document.getElementById(
            "race"
        ),

    physicalDescription:
        document.getElementById(
            "physicalDescription"
        ),

    appearance:
        document.getElementById(
            "appearance"
        )

};


// =========================================================
// CARICAMENTO DATI DAL BACKEND
// =========================================================
//
// Le razze e le lingue NON sono definite nel frontend.
//
// Il frontend chiede i dati al server:
//
// GET /api/races
// GET /api/languages
//
// =========================================================

async function loadWorldData() {

    // -----------------------------------------------------
    // RAZZE
    // -----------------------------------------------------

    const racesResponse =
        await fetch(
            "/api/races"
        );


    if (!racesResponse.ok) {

        throw new Error(
            "Impossibile caricare le razze."
        );

    }


    availableRaces =
        await racesResponse.json();


    // -----------------------------------------------------
    // LINGUE
    // -----------------------------------------------------

    const languagesResponse =
        await fetch(
            "/api/languages"
        );


    if (!languagesResponse.ok) {

        throw new Error(
            "Impossibile caricare le lingue."
        );

    }


    availableLanguages =
        await languagesResponse.json();

}


// =========================================================
// TROVA RAZZA
// =========================================================

function findRace(
    raceName
) {

    if (
        !raceName ||
        !Array.isArray(
            availableRaces
        )
    ) {

        return null;

    }


    return availableRaces.find(
        race =>
            String(
                race.name
            ).toLowerCase() ===
            String(
                raceName
            ).trim().toLowerCase()
    ) || null;

}


// =========================================================
// TROVA LINGUA
// =========================================================

function findLanguage(
    languageName
) {

    if (
        !languageName ||
        !Array.isArray(
            availableLanguages
        )
    ) {

        return null;

    }


    return availableLanguages.find(
        language =>
            String(
                language.name
            ).toLowerCase() ===
            String(
                languageName
            ).trim().toLowerCase()
    ) || null;

}


// =========================================================
// NOMI DELLE RAZZE
// =========================================================

function getRaceNames() {

    return availableRaces.map(
        race =>
            race.name
    );

}


// =========================================================
// NOMI DELLE LINGUE
// =========================================================

function getLanguageNames() {

    return availableLanguages.map(
        language =>
            language.name
    );

}

// =========================================================
// NAVIGAZIONE
// =========================================================

function initializeNavigation() {

    const buttons =
        document.querySelectorAll(
            ".nav-button"
        );


    buttons.forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    if (
                        button.classList.contains(
                            "disabled"
                        )
                    ) {
                        return;
                    }


                    const section =
                        button.dataset.section;


                    if (!section) {
                        return;
                    }


                    showSection(
                        section
                    );


                    buttons.forEach(
                        otherButton => {

                            otherButton.classList.remove(
                                "active"
                            );

                        }
                    );


                    button.classList.add(
                        "active"
                    );

                }
            );

        }
    );

}


// =========================================================
// MOSTRA SEZIONE
// =========================================================

function showSection(
    section
) {

    const sections =
        document.querySelectorAll(
            ".section"
        );


    sections.forEach(
        element => {

            element.classList.add(
                "hidden"
            );

        }
    );


    const target =
        document.getElementById(
            `${section}Section`
        );


    if (!target) {
        return;
    }


    target.classList.remove(
        "hidden"
    );

}


// =========================================================
// INIZIALIZZA SELETTORE RAZZE
// =========================================================

function initializeRaceSelector() {

    if (!inputs.race) {
        return;
    }


    if (
        inputs.race.tagName.toLowerCase() !==
        "select"
    ) {
        return;
    }


    inputs.race.innerHTML = "";


    // -----------------------------------------------------
    // PLACEHOLDER
    // -----------------------------------------------------

    const placeholder =
        document.createElement(
            "option"
        );


    placeholder.value =
        "";


    placeholder.textContent =
        "Seleziona razza";


    placeholder.disabled =
        true;


    placeholder.selected =
        true;


    inputs.race.appendChild(
        placeholder
    );


    // -----------------------------------------------------
    // RAZZE DAL BACKEND
    // -----------------------------------------------------

    availableRaces.forEach(
        race => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                race.name;


            option.textContent =
                race.name;


            inputs.race.appendChild(
                option
            );

        }
    );


    // -----------------------------------------------------
    // CAMBIO RAZZA
    // -----------------------------------------------------

    inputs.race.addEventListener(
        "change",
        handleRaceChange
    );

}


// =========================================================
// CAMBIO RAZZA
// =========================================================

function handleRaceChange() {

    if (!character) {
        return;
    }


    const race =
        inputs.race.value.trim();


    if (!race) {
        return;
    }


    const raceData =
        findRace(
            race
        );


    if (!raceData) {

        console.warn(
            "Razza non valida:",
            race
        );

        return;
    }


    // -----------------------------------------------------
    // AGGIORNA IDENTITÀ
    // -----------------------------------------------------

    if (
        character.identity
    ) {

        character.identity.race =
            race;

    }


    updateCharacterTitle();

}


