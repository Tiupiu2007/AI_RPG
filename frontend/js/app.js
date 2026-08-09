// =========================================================
// AI RPG - CHARACTER EDITOR
// =========================================================
//
// Stato principale dell'interfaccia.
// Razze e lingue arrivano dal backend.
// Il personaggio viene mantenuto anche in localStorage.
//
// =========================================================

let character = null;
let availableRaces = [];
let availableLanguages = [];

const STORAGE_KEY = "ai-rpg-character";

// =========================================================
// ELEMENTI DOM
// =========================================================

const generateButton = document.getElementById("generateButton");
const newCharacterButton = document.getElementById("newCharacterButton");
const saveButton = document.getElementById("saveButton");
const overlay = document.getElementById("generationOverlay");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const generationStatus = document.getElementById("generationStatus");
const generationName = document.getElementById("generationName");

const inputs = {
    name: document.getElementById("name"),
    surname: document.getElementById("surname"),
    nickname: document.getElementById("nickname"),
    age: document.getElementById("age"),
    birthDate: document.getElementById("birthDate"),
    sex: document.getElementById("sex"),
    race: document.getElementById("race"),
    physicalDescription: document.getElementById("physicalDescription"),
    appearance: document.getElementById("appearance")
};

// =========================================================
// PERSONAGGIO VUOTO
// =========================================================

function createEmptyCharacter() {
    return {
        identity: {
            name: "",
            surname: "",
            nickname: "",
            age: 0,
            birth_date: "",
            sex: "",
            race: "",
            physical_description: "",
            appearance: ""
        },
        languages: []
    };
}

function normalizeCharacter(value) {
    const empty = createEmptyCharacter();

    if (!value || typeof value !== "object") {
        return empty;
    }

    const identity = value.identity || {};

    return {
        identity: {
            ...empty.identity,
            ...identity,
            age: Number.isFinite(Number(identity.age)) ? Number(identity.age) : 0
        },
        languages: Array.isArray(value.languages) ? value.languages : []
    };
}

// =========================================================
// CARICAMENTO DATI DAL BACKEND
// =========================================================

async function loadWorldData() {
    const racesResponse = await fetch("/api/races");

    if (!racesResponse.ok) {
        throw new Error("Impossibile caricare le razze.");
    }

    availableRaces = await racesResponse.json();

    const languagesResponse = await fetch("/api/languages");

    if (!languagesResponse.ok) {
        throw new Error("Impossibile caricare le lingue.");
    }

    availableLanguages = await languagesResponse.json();
}

// =========================================================
// RICERCA DATI
// =========================================================

function findRace(raceName) {
    if (!raceName) return null;

    return availableRaces.find(
        race => String(race.name).trim().toLowerCase() === String(raceName).trim().toLowerCase()
    ) || null;
}

function findLanguage(languageName) {
    if (!languageName) return null;

    return availableLanguages.find(
        language => String(language.name).trim().toLowerCase() === String(languageName).trim().toLowerCase()
    ) || null;
}

// =========================================================
// NAVIGAZIONE
// =========================================================

function initializeNavigation() {
    const buttons = document.querySelectorAll(".nav-button");

    buttons.forEach(button => {
        button.addEventListener("click", () => {
            if (button.classList.contains("disabled")) return;

            const section = button.dataset.section;
            if (!section) return;

            showSection(section);

            buttons.forEach(other => other.classList.remove("active"));
            button.classList.add("active");
        });
    });
}

function showSection(section) {
    document.querySelectorAll(".section").forEach(element => {
        element.classList.add("hidden");
    });

    const target = document.getElementById(`${section}Section`);

    if (target) {
        target.classList.remove("hidden");
    }
}

function activateSection(section) {
    showSection(section);

    document.querySelectorAll(".nav-button").forEach(button => {
        button.classList.toggle("active", button.dataset.section === section);
    });
}

// =========================================================
// SELETTORE RAZZA
// =========================================================

function initializeRaceSelector() {
    if (!inputs.race || inputs.race.tagName.toLowerCase() !== "select") return;

    inputs.race.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Seleziona razza";
    placeholder.disabled = true;
    inputs.race.appendChild(placeholder);

    availableRaces.forEach(race => {
        const option = document.createElement("option");
        option.value = race.name;
        option.textContent = race.name;
        inputs.race.appendChild(option);
    });

    inputs.race.addEventListener("change", handleRaceChange);
}

// =========================================================
// CAMBIO RAZZA
// =========================================================

async function handleRaceChange() {
    if (!character) return;

    const raceName = inputs.race.value.trim();
    const race = findRace(raceName);

    if (!race) return;

    character.identity.race = race.name;

    // Le lingue dipendono dalla razza e vengono ricalcolate dal backend.
    try {
        const response = await fetch("/api/race-languages", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ race: race.name })
        });

        if (!response.ok) {
            throw new Error("Impossibile caricare le lingue della razza.");
        }

        character.languages = await response.json();
        loadLanguages();
    } catch (error) {
        console.error(error);
        character.languages = [];
        loadLanguages();
    }

    saveLocalCharacter();
    updateCharacterTitle();
}

// =========================================================
// CARICAMENTO PERSONAGGIO
// =========================================================

function loadCharacter() {
    let saved = null;

    try {
        saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    } catch (error) {
        console.warn("Salvataggio locale non valido.", error);
    }

    character = normalizeCharacter(saved);
    loadCharacterIntoUI();
}

function loadCharacterIntoUI() {
    const identity = character.identity;

    inputs.name.value = identity.name || "";
    inputs.surname.value = identity.surname || "";
    inputs.nickname.value = identity.nickname || "";
    inputs.age.value = identity.age ?? 0;
    inputs.birthDate.value = identity.birth_date || "";
    inputs.sex.value = identity.sex || "";
    inputs.race.value = identity.race || "";
    inputs.physicalDescription.value = identity.physical_description || "";
    inputs.appearance.value = identity.appearance || "";

    loadLanguages();
    updateCharacterTitle();
}

// =========================================================
// LINGUE
// =========================================================

function loadLanguages() {
    const list = document.getElementById("languagesList");
    if (!list) return;

    list.innerHTML = "";

    if (!character.languages.length) {
        const empty = document.createElement("div");
        empty.className = "empty-language";
        empty.textContent = "Nessuna lingua conosciuta.";
        list.appendChild(empty);
        return;
    }

    character.languages.forEach(language => {
        const item = document.createElement("div");
        item.className = "language-item";

        const name = document.createElement("div");
        name.className = "language-name";
        name.textContent = language.name || "Lingua sconosciuta";
        item.appendChild(name);

        const levels = document.createElement("div");
        levels.className = "language-level-values";

        addLanguageLevel(levels, "Comprensione", language.comprehension);
        addLanguageLevel(levels, "Parlato", language.speaking);
        addLanguageLevel(levels, "Scrittura", language.writing);

        item.appendChild(levels);
        list.appendChild(item);
    });
}

function addLanguageLevel(container, label, value) {
    const row = document.createElement("div");
    row.className = "language-value-row";

    const text = document.createElement("span");
    text.textContent = label;

    const valueText = document.createElement("span");
    valueText.textContent = `${Math.round(Number(value || 0) * 100)}%`;

    row.appendChild(text);
    row.appendChild(valueText);
    container.appendChild(row);
}

// =========================================================
// GUI -> PERSONAGGIO
// =========================================================

function updateCharacterFromUI() {
    if (!character) return;

    character.identity.name = inputs.name.value.trim();
    character.identity.surname = inputs.surname.value.trim();
    character.identity.nickname = inputs.nickname.value.trim();
    character.identity.age = Number(inputs.age.value) || 0;
    character.identity.birth_date = inputs.birthDate.value.trim();
    character.identity.sex = inputs.sex.value.trim();
    character.identity.race = inputs.race.value.trim();
    character.identity.physical_description = inputs.physicalDescription.value.trim();
    character.identity.appearance = inputs.appearance.value.trim();

    saveLocalCharacter();
    updateCharacterTitle();
}

function initializeInputListeners() {
    Object.values(inputs).forEach(input => {
        if (!input) return;

        input.addEventListener("input", updateCharacterFromUI);
    });
}

// =========================================================
// TITOLO
// =========================================================

function updateCharacterTitle() {
    const title = document.getElementById("characterTitle");
    if (!title || !character) return;

    const name = character.identity.name || "";
    const surname = character.identity.surname || "";
    const fullName = `${name} ${surname}`.trim();

    title.textContent = fullName || "Nuovo personaggio";
}

// =========================================================
// NUOVO PERSONAGGIO
// =========================================================

function newCharacter() {
    if (!confirm("Creare un nuovo personaggio? Le modifiche non salvate verranno perse.")) {
        return;
    }

    character = createEmptyCharacter();
    localStorage.removeItem(STORAGE_KEY);
    loadCharacterIntoUI();
    activateSection("identity");
}

// =========================================================
// SALVATAGGIO
// =========================================================

function saveLocalCharacter() {
    if (!character) return;

    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(character)
    );
}

function saveCharacter() {
    updateCharacterFromUI();
    saveLocalCharacter();

    alert("Personaggio salvato.");
}

// =========================================================
// GENERAZIONE IA
// =========================================================

async function generateCharacter() {
    if (generateButton.disabled) return;

    generateButton.disabled = true;
    newCharacterButton.disabled = true;

    overlay.classList.remove("hidden");
    resetGeneration();

    try {
        setGenerationStep("stepRace", "active");
        setProgress(10, "Scelta della razza...");

        const response = await fetch("/api/generate-character", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || "Generazione fallita.");
        }

        const generated = await response.json();

        setGenerationStep("stepRace", "completed");
        setGenerationStep("stepIdentity", "active");
        setProgress(35, "Identità generata...");

        await wait(250);

        setGenerationStep("stepIdentity", "completed");
        setGenerationStep("stepLanguages", "active");
        setProgress(55, "Lingue della razza...");

        await wait(250);

        setGenerationStep("stepLanguages", "completed");
        setGenerationStep("stepAppearance", "active");
        setProgress(70, "Controllo dell'aspetto...");

        await wait(250);

        setGenerationStep("stepAppearance", "completed");
        setGenerationStep("stepConsistency", "active");
        setProgress(85, "Controllo della coerenza...");

        await wait(250);

        character = normalizeCharacter(generated);
        saveLocalCharacter();
        loadCharacterIntoUI();

        setGenerationStep("stepConsistency", "completed");
        setGenerationStep("stepComplete", "active");
        setProgress(95, "Completamento della scheda...");

        await wait(250);

        setGenerationStep("stepComplete", "completed");
        setProgress(100, "Personaggio completato.");

        generationName.textContent = `${character.identity.name} ${character.identity.surname}`.trim();

        await wait(700);
        overlay.classList.add("hidden");

    } catch (error) {
        console.error("Errore durante la generazione:", error);
        generationName.textContent = "Generazione fallita";
        setProgress(100, error.message);
        alert(`Non è stato possibile generare il personaggio.\n\n${error.message}`);
        await wait(700);
        overlay.classList.add("hidden");
    } finally {
        generateButton.disabled = false;
        newCharacterButton.disabled = false;
    }
}

// =========================================================
// OVERLAY
// =========================================================

function resetGeneration() {
    setProgress(0, "L'IA sta preparando il personaggio...");
    generationName.textContent = "Generazione in corso...";

    [
        "stepRace",
        "stepIdentity",
        "stepLanguages",
        "stepAppearance",
        "stepConsistency",
        "stepComplete"
    ].forEach(id => {
        const element = document.getElementById(id);
        if (!element) return;

        element.classList.remove("active", "completed");

        const symbol = element.querySelector("span");
        if (symbol) symbol.textContent = "○";
    });
}

function setProgress(value, status) {
    if (progressBar) progressBar.style.width = `${value}%`;
    if (progressText) progressText.textContent = `${value}%`;
    if (generationStatus) generationStatus.textContent = status;
}

function setGenerationStep(id, state) {
    const element = document.getElementById(id);
    if (!element) return;

    element.classList.remove("active", "completed");

    const symbol = element.querySelector("span");

    if (state === "active") {
        element.classList.add("active");
        if (symbol) symbol.textContent = "◉";
    }

    if (state === "completed") {
        element.classList.add("completed");
        if (symbol) symbol.textContent = "✓";
    }
}

function wait(milliseconds) {
    return new Promise(resolve => setTimeout(resolve, milliseconds));
}

// =========================================================
// EVENTI
// =========================================================

function initializeEvents() {
    generateButton?.addEventListener("click", generateCharacter);
    newCharacterButton?.addEventListener("click", newCharacter);
    saveButton?.addEventListener("click", saveCharacter);
}

// =========================================================
// AVVIO
// =========================================================

async function initializeApp() {
    try {
        await loadWorldData();
        initializeNavigation();
        initializeRaceSelector();
        initializeInputListeners();
        initializeEvents();
        loadCharacter();
    } catch (error) {
        console.error("Errore avvio interfaccia:", error);
        alert(`Impossibile avviare l'interfaccia.\n\n${error.message}`);
    }
}

initializeApp();
