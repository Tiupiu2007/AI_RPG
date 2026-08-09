import { createEmptyCharacter, loadLocalCharacter, saveLocalCharacter, clearLocalCharacter } from "./character-state.js";
import { loadWorldData, getRaceLanguages } from "./character-api.js";
import { loadProfileIntoUI, updateProfileFromUI, bindProfileInputs } from "./profile.js";
import { initializeNavigation, activateSection, updateCharacterTitle } from "./character-ui.js";
import { generateCharacter } from "./character-generation.js";
import { updateSummary } from "./character-summary.js";
import { initializeCharacterDescriptionUI } from "./character-description.js";

let character = null;
let availableRaces = [];

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
    if (!character) return;
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
    if (!confirm("Creare un nuovo personaggio? Le modifiche non salvate verranno perse.")) return;
    character = createEmptyCharacter();
    clearLocalCharacter();
    loadCharacterIntoUI();
    const description = document.getElementById("characterDescription");
    if (description) description.value = "";
    activateSection("identity");
}

function onGenerated(generated) {
    character = generated;
    loadCharacterIntoUI();
}

async function runGeneration(options = {}) {
    try { await generateCharacter(onGenerated, options); }
    catch { /* L'errore viene già mostrato dal modulo di generazione. */ }
}

async function initializeApp() {
    try {
        initializeCharacterDescriptionUI();
        const world = await loadWorldData();
        availableRaces = world.races;
        initializeNavigation();
        initializeRaceSelector();
        initializeInputListeners();
        document.getElementById("generateButton")?.addEventListener("click", () => runGeneration());
        window.addEventListener("ai-rpg-generate-character", event => runGeneration(event.detail || {}));
        document.getElementById("newCharacterButton")?.addEventListener("click", newCharacter);
        character = loadLocalCharacter();
        loadCharacterIntoUI();
    } catch (error) {
        console.error("Errore avvio interfaccia:", error);
        alert(`Impossibile avviare l'interfaccia.\n\n${error.message}`);
    }
}

initializeApp();
