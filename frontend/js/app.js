import { createEmptyCharacter, loadLocalCharacter, saveLocalCharacter, clearLocalCharacter } from "./character-state.js";
import { loadWorldData, getRaceLanguages, resetCharacterHistory } from "./character-api.js";
import { loadProfileIntoUI, updateProfileFromUI, bindProfileInputs } from "./profile.js";
import { initializeNavigation, activateSection, updateCharacterTitle } from "./character-ui.js";
import { generateCharacter } from "./character-generation.js";
import { updateSummary } from "./character-summary.js";
import { initializeCharacterDescriptionUI } from "./character-description.js";

let character = null;
let availableRaces = [];

const urlParams = new URLSearchParams(window.location.search);
const pvpRoomId = urlParams.get("room");
const pvpToken = urlParams.get("token");
const playerSheetMode = Boolean(pvpRoomId && pvpToken);

const inputs = {
    name: document.getElementById("name"), surname: document.getElementById("surname"),
    nickname: document.getElementById("nickname"), age: document.getElementById("age"),
    birthDate: document.getElementById("birthDate"), sex: document.getElementById("sex"),
    race: document.getElementById("race"), physicalDescription: document.getElementById("physicalDescription"),
    appearance: document.getElementById("appearance")
};

function findRace(name) {
    return availableRaces.find(race => String(race.name).trim().toLowerCase() === String(name || "").trim().toLowerCase()) || null;
}

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

async function handleRaceChange() {
    if (!character || playerSheetMode) return;
    const race = findRace(inputs.race.value);
    if (!race) return;
    character.identity.race = race.name;
    try { character.languages = await getRaceLanguages(race.name); }
    catch (error) { console.error("Errore lingue razza:", error); character.languages = []; }
    saveLocalCharacter(character);
    window.dispatchEvent(new CustomEvent("ai-rpg-character-changed"));
    updateCharacterTitle(character);
    updateSummary(character);
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
    loadProfileIntoUI(character);
    updateCharacterTitle(character);
    updateSummary(character);
    if (window.aiRpgCharacterSections?.setData) window.aiRpgCharacterSections.setData(character.extra);
    window.dispatchEvent(new CustomEvent("ai-rpg-character-changed"));
}

function updateCharacterFromUI() {
    if (!character || playerSheetMode) return;
    character.identity.name = inputs.name.value.trim();
    character.identity.surname = inputs.surname.value.trim();
    character.identity.nickname = inputs.nickname.value.trim();
    character.identity.age = Number(inputs.age.value) || 0;
    character.identity.birth_date = inputs.birthDate.value.trim();
    character.identity.sex = inputs.sex.value.trim();
    character.identity.race = inputs.race.value.trim();
    character.identity.physical_description = inputs.physicalDescription.value.trim();
    character.identity.appearance = inputs.appearance.value.trim();
    updateProfileFromUI(character);
    if (window.aiRpgCharacterSections?.getData) character.extra = window.aiRpgCharacterSections.getData();
    saveLocalCharacter(character);
    updateCharacterTitle(character);
    updateSummary(character);
}

function initializeInputListeners() {
    Object.values(inputs).forEach(input => input?.addEventListener("input", updateCharacterFromUI));
    bindProfileInputs(updateCharacterFromUI);
}

function newCharacter() {
    if (playerSheetMode) return;
    if (!confirm("Creare un nuovo personaggio? Le modifiche non salvate verranno perse.")) return;
    character = createEmptyCharacter();
    clearLocalCharacter();
    loadCharacterIntoUI();
    const description = document.getElementById("characterDescription");
    if (description) description.value = "";
    activateSection("identity");
}

async function resetCurrentCharacterHistory() {
    if (playerSheetMode) {
        alert("La gestione della memoria è riservata al server.");
        return;
    }
    if (!character?.id) {
        alert("Seleziona prima un personaggio salvato.");
        return;
    }

    const confirmed = confirm(
        "Azzerare memoria, eventi e conversazione persistente di questo personaggio?\n\n" +
        "Il personaggio e le relazioni verranno mantenuti."
    );
    if (!confirmed) return;

    try {
        const result = await resetCharacterHistory(character.id, false);
        if (character.extra && typeof character.extra === "object") {
            delete character.extra.conversation;
            delete character.extra.state;
        }
        saveLocalCharacter(character);
        window.dispatchEvent(new CustomEvent("ai-rpg-character-history-reset", { detail: result }));
        alert(`Memoria resettata.\nMemorie: ${result.memories_deleted}\nEventi: ${result.events_deleted}`);
    } catch (error) {
        console.error("Errore reset memoria:", error);
        alert(`Reset memoria fallito.\n\n${error.message}`);
    }
}

window.aiRpgResetCharacterHistory = resetCurrentCharacterHistory;

function onGenerated(generated) {
    character = generated;
    loadCharacterIntoUI();
}

async function runGeneration(options = {}) {
    if (playerSheetMode) return;
    try { await generateCharacter(onGenerated, options); }
    catch { /* L'errore viene già mostrato dal modulo di generazione. */ }
}

function addArenaButton() {
    const actions = document.querySelector(".topbar-actions");
    if (!actions || document.getElementById("arenaButton")) return;
    if (playerSheetMode) return;
    const button = document.createElement("button");
    button.id = "arenaButton";
    button.className = "secondary-button";
    button.textContent = "⚔ Arena";
    button.title = "Simula uno scontro tra due personaggi";
    button.addEventListener("click", () => { window.location.href = "/battle.html"; });
    actions.appendChild(button);
}

function lockPlayerSheet() {
    document.body.classList.add("pvp-player-sheet");

    const pageLabel = document.querySelector(".page-label");
    if (pageLabel) pageLabel.textContent = "SCHEDA PERSONAGGIO · PVP";

    const title = document.getElementById("characterTitle");
    if (title) title.textContent = "Il tuo personaggio";

    document.querySelectorAll(".topbar-actions").forEach(element => {
        element.innerHTML = '<span class="player-sheet-badge">👤 SOLO VISUALIZZAZIONE</span>';
    });

    document.querySelectorAll(".character-list-title, .character-search, #characterList").forEach(element => {
        element.style.display = "none";
    });

    // La navigazione delle sezioni resta disponibile, ma tutti i controlli
    // che possono cambiare dati vengono resi non modificabili.
    document.querySelectorAll("#content input, #content textarea").forEach(element => {
        element.readOnly = true;
        element.setAttribute("aria-readonly", "true");
    });
    document.querySelectorAll("#content select").forEach(element => {
        element.disabled = true;
    });
    document.querySelectorAll("#content button").forEach(element => {
        element.disabled = true;
    });

    // Le tab di navigazione sono solo visualizzazione e devono continuare a funzionare.
    document.querySelectorAll(".sidebar .nav-button").forEach(element => {
        element.disabled = false;
    });
}

async function initializePlayerSheet() {
    const roomResponse = await fetch(`/api/pvp/${encodeURIComponent(pvpRoomId)}?token=${encodeURIComponent(pvpToken)}`);
    const roomData = await roomResponse.json().catch(() => ({}));
    if (!roomResponse.ok) throw new Error(roomData.error || "Link PvP non valido o scaduto.");
    if (roomData.is_spectator || !Number.isInteger(Number(roomData.you_are))) {
        throw new Error("Il link spettatore non può aprire una scheda personaggio.");
    }

    const characterId = Number(roomData.you_are);
    const response = await fetch(`/api/characters/${characterId}?room=${encodeURIComponent(pvpRoomId)}&token=${encodeURIComponent(pvpToken)}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Non è possibile caricare il tuo personaggio.");

    character = data;
    lockPlayerSheet();
    loadCharacterIntoUI();
}

async function initializeApp() {
    try {
        initializeCharacterDescriptionUI();
        const world = await loadWorldData();
        availableRaces = world.races;
        initializeNavigation();
        initializeRaceSelector();
        initializeInputListeners();

        if (playerSheetMode) {
            await initializePlayerSheet();
            return;
        }

        addArenaButton();
        document.getElementById("generateButton")?.addEventListener("click", () => runGeneration());
        window.addEventListener("ai-rpg-generate-character", event => runGeneration(event.detail || {}));
        window.addEventListener("ai-rpg-reset-character-history", resetCurrentCharacterHistory);
        document.getElementById("newCharacterButton")?.addEventListener("click", newCharacter);
        document.getElementById("resetHistoryButton")?.addEventListener("click", resetCurrentCharacterHistory);
        character = loadLocalCharacter();
        loadCharacterIntoUI();
    } catch (error) {
        console.error("Errore avvio interfaccia:", error);
        alert(`Impossibile avviare l'interfaccia.\n\n${error.message}`);
    }
}

initializeApp();
