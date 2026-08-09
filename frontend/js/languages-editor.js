// =========================================================
// AI RPG - LANGUAGE EDITOR
// =========================================================
//
// Editor delle lingue del personaggio.
// I dati vengono mantenuti in localStorage e inviati al
// database quando si preme Salva.
//
// =========================================================

const LANGUAGE_STORAGE_KEY = "ai-rpg-character";

const languageList = document.getElementById("languagesList");
const languageAddButton = document.getElementById("addLanguageButton");
const languageSelect = document.getElementById("languageSelect");

function readCharacter() {
    try {
        return JSON.parse(localStorage.getItem(LANGUAGE_STORAGE_KEY));
    } catch {
        return null;
    }
}

function writeCharacter(character) {
    localStorage.setItem(
        LANGUAGE_STORAGE_KEY,
        JSON.stringify(character)
    );
}

function normalizeLevel(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.max(0, Math.min(1, number));
}

function levelPercent(value) {
    return Math.round(normalizeLevel(value) * 100);
}

function getLevelLabel(value) {
    const percent = levelPercent(value);

    if (percent <= 0) return "Sconosciuta";
    if (percent < 35) return "Conoscenza iniziale";
    if (percent < 55) return "Conoscenza parziale";
    if (percent < 75) return "Buona conoscenza";
    if (percent < 95) return "Molto buona";
    return "Fluente";
}

function saveCurrentCharacter(character) {
    if (!character) return;
    writeCharacter(character);
    window.dispatchEvent(new CustomEvent("ai-rpg-character-changed"));
}

function renderLanguageSelect(languages) {
    if (!languageSelect) return;

    languageSelect.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Seleziona una lingua";
    placeholder.disabled = true;
    placeholder.selected = true;
    languageSelect.appendChild(placeholder);

    languages.forEach(language => {
        const option = document.createElement("option");
        option.value = language.name;
        option.textContent = language.name;
        languageSelect.appendChild(option);
    });
}

function createLevelControl(language, field, label) {
    const row = document.createElement("div");
    row.className = "language-editor-level";

    const header = document.createElement("div");
    header.className = "language-editor-level-header";

    const title = document.createElement("span");
    title.textContent = label;

    const value = document.createElement("span");
    value.className = "language-editor-level-value";
    value.textContent = `${levelPercent(language[field])}% · ${getLevelLabel(language[field])}`;

    header.appendChild(title);
    header.appendChild(value);

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.step = "1";
    slider.value = String(levelPercent(language[field]));

    slider.addEventListener("input", () => {
        language[field] = Number(slider.value) / 100;
        value.textContent = `${slider.value}% · ${getLevelLabel(language[field])}`;

        const character = readCharacter();
        if (!character) return;

        character.languages = Array.isArray(character.languages)
            ? character.languages
            : [];

        saveCurrentCharacter(character);
    });

    row.appendChild(header);
    row.appendChild(slider);

    return row;
}

function renderLanguages() {
    if (!languageList) return;

    const character = readCharacter();
    const languages = character && Array.isArray(character.languages)
        ? character.languages
        : [];

    languageList.innerHTML = "";

    if (!languages.length) {
        const empty = document.createElement("div");
        empty.className = "empty-language";
        empty.textContent = "Nessuna lingua conosciuta.";
        languageList.appendChild(empty);
        return;
    }

    languages.forEach((language, index) => {
        const item = document.createElement("div");
        item.className = "language-editor-item";

        const top = document.createElement("div");
        top.className = "language-editor-top";

        const name = document.createElement("div");
        name.className = "language-editor-name";
        name.textContent = language.name || "Lingua sconosciuta";

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "language-remove-button";
        remove.textContent = "Rimuovi";
        remove.addEventListener("click", () => {
            const current = readCharacter();
            if (!current || !Array.isArray(current.languages)) return;

            current.languages.splice(index, 1);
            saveCurrentCharacter(current);
            renderLanguages();
        });

        top.appendChild(name);
        top.appendChild(remove);

        item.appendChild(top);
        item.appendChild(createLevelControl(language, "comprehension", "Comprensione"));
        item.appendChild(createLevelControl(language, "speaking", "Parlato"));
        item.appendChild(createLevelControl(language, "writing", "Scrittura"));

        languageList.appendChild(item);
    });
}

async function loadAvailableLanguages() {
    if (!languageSelect) return;

    try {
        const response = await fetch("/api/languages");
        if (!response.ok) throw new Error("Impossibile caricare le lingue.");

        const languages = await response.json();
        renderLanguageSelect(languages);
    } catch (error) {
        console.error("Errore caricamento lingue:", error);
    }
}

function addSelectedLanguage() {
    const selectedName = languageSelect?.value?.trim();
    if (!selectedName) return;

    const character = readCharacter();
    if (!character) {
        alert("Crea o genera prima un personaggio.");
        return;
    }

    character.languages = Array.isArray(character.languages)
        ? character.languages
        : [];

    if (character.languages.some(language =>
        String(language.name).toLowerCase() === selectedName.toLowerCase()
    )) {
        alert("Questa lingua è già presente nel personaggio.");
        return;
    }

    character.languages.push({
        language_id: selectedName.toLowerCase().replaceAll(" ", "_"),
        name: selectedName,
        comprehension: 0,
        speaking: 0,
        writing: 0
    });

    saveCurrentCharacter(character);
    renderLanguages();
    languageSelect.selectedIndex = 0;
}

languageAddButton?.addEventListener("click", addSelectedLanguage);
window.addEventListener("ai-rpg-character-changed", renderLanguages);
window.addEventListener("storage", renderLanguages);

loadAvailableLanguages();
renderLanguages();
