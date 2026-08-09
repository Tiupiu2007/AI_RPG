const EXTRA_KEY = "ai-rpg-character-extra";
const STAT_NAMES = ["strength","constitution","agility","intelligence","perception","willpower","charisma","luck"];

const DEFAULT_EXTRA = {
    level: 1,
    summary: "",
    statistics: Object.fromEntries(STAT_NAMES.map(name => [name, 10])),
    abilities: [],
    skills: [],
    conditions: { health: 100, stamina: 100, mana: 0, status: "Normale" },
    relationships: []
};

let extra = loadExtra();

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}

function cloneDefaultExtra() {
    return clone(DEFAULT_EXTRA);
}

function calculateLevel(statistics) {
    const values = STAT_NAMES.map(name => Number(statistics?.[name]) || 0);
    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    return Math.max(1, Math.min(20, 1 + Math.floor(Math.max(0, average - 25) / 3.5)));
}

function getCharacterFromStorage() {
    try {
        const value = JSON.parse(localStorage.getItem("ai-rpg-character"));
        return value && typeof value === "object" ? value : null;
    } catch (_) {
        return null;
    }
}

function getFocus(statistics) {
    const labels = {
        strength: "forza fisica", constitution: "resistenza", agility: "agilità",
        intelligence: "intelligenza", perception: "percezione", willpower: "volontà",
        charisma: "carisma", luck: "fortuna"
    };

    const ranked = STAT_NAMES
        .map(name => ({ name, value: Number(statistics?.[name]) || 0 }))
        .sort((a, b) => b.value - a.value);

    return labels[ranked[0]?.name] || "versatilità";
}

function buildSummary() {
    const character = getCharacterFromStorage();
    if (!character) return "Genera un personaggio per ottenere un riepilogo completo.";

    const identity = character.identity || {};
    const psychology = character.psychology || {};
    const personality = character.personality || {};
    const race = identity.race || "razza sconosciuta";
    const age = Number(identity.age) || 0;
    const focus = getFocus(extra.statistics);

    const personalityText = personality.personality_description || personality.traits || "Ha una personalità ancora da definire.";
    const desireText = psychology.desires ? ` Il suo principale obiettivo è ${psychology.desires}.` : "";
    const fearText = psychology.fears ? ` Tra le sue paure spicca ${psychology.fears}.` : "";

    return `${identity.name || "Questo personaggio"} è ${age > 0 ? `un individuo di ${age} anni` : "un individuo"} di razza ${race}, con una predisposizione naturale verso la ${focus}. ${personalityText}${desireText}${fearText}`.replace(/\s+/g, " ").trim();
}

function normalizeExtra(value) {
    const base = cloneDefaultExtra();
    if (!value || typeof value !== "object") return base;

    const statistics = { ...base.statistics, ...(value.statistics || {}) };
    const level = Number(value.level) > 0 ? Number(value.level) : calculateLevel(statistics);

    return {
        level: Math.max(1, Math.min(20, Math.round(level))),
        summary: typeof value.summary === "string" ? value.summary : "",
        statistics,
        abilities: Array.isArray(value.abilities) ? value.abilities : [],
        skills: Array.isArray(value.skills) ? value.skills : [],
        conditions: { ...base.conditions, ...(value.conditions || {}) },
        relationships: Array.isArray(value.relationships) ? value.relationships : []
    };
}

function refreshDerivedData() {
    extra.level = calculateLevel(extra.statistics);
    extra.summary = buildSummary();
}

function loadExtra() {
    try {
        const local = JSON.parse(localStorage.getItem(EXTRA_KEY));
        const normalized = normalizeExtra(local);
        return normalized;
    } catch (_) {
        return cloneDefaultExtra();
    }
}

function saveExtra() {
    refreshDerivedData();
    localStorage.setItem(EXTRA_KEY, JSON.stringify(extra));
    syncWithCharacterStorage();
    renderSummary();
}

function syncWithCharacterStorage() {
    try {
        const character = getCharacterFromStorage();
        if (!character) return;
        character.extra = { ...(character.extra || {}), ...clone(extra) };
        localStorage.setItem("ai-rpg-character", JSON.stringify(character));
    } catch (_) {}
}

function esc(value) {
    return String(value ?? "").replace(/[&<>\"]/g, char => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[char]));
}

function labelForStat(key) {
    return {
        strength: "Forza", constitution: "Costituzione", agility: "Agilità",
        intelligence: "Intelligenza", perception: "Percezione", willpower: "Volontà",
        charisma: "Carisma", luck: "Fortuna"
    }[key] || key;
}

function levelDescription(level) {
    if (level <= 3) return "Principiante";
    if (level <= 6) return "Alle prime esperienze";
    if (level <= 10) return "Competente";
    if (level <= 14) return "Esperto";
    if (level <= 17) return "Veterano";
    return "Eccezionale";
}

function renderStatistics() {
    const root = document.getElementById("statisticsEditor");
    if (!root) return;
    root.innerHTML = "";

    STAT_NAMES.forEach(key => {
        const value = Number(extra.statistics[key]) || 0;
        root.insertAdjacentHTML("beforeend", `
            <div class="stat-row">
                <span>${labelForStat(key)}</span>
                <input type="number" min="0" max="100" data-stat="${key}" value="${value}">
            </div>`);
    });

    root.querySelectorAll("[data-stat]").forEach(input => {
        input.addEventListener("input", () => {
            extra.statistics[input.dataset.stat] = Math.max(0, Math.min(100, Number(input.value) || 0));
            saveExtra();
            renderLevel();
        });
    });
}

function renderLevel() {
    const level = Math.max(1, Math.round(extra.level || calculateLevel(extra.statistics)));
    const levelElement = document.getElementById("characterLevel");
    const textElement = document.getElementById("characterLevelText");
    const badge = document.getElementById("summaryLevelBadge");

    if (levelElement) levelElement.textContent = level;
    if (textElement) textElement.textContent = levelDescription(level);
    if (badge) badge.textContent = `LIV. ${level}`;
}

function renderSummary() {
    const character = getCharacterFromStorage();
    const identity = character?.identity || {};
    const psychology = character?.psychology || {};
    const status = extra.conditions?.status || "Normale";

    const title = document.getElementById("summaryTitle");
    const text = document.getElementById("summaryText");
    const race = document.getElementById("summaryRace");
    const age = document.getElementById("summaryAge");
    const focus = document.getElementById("summaryFocus");
    const summaryStatus = document.getElementById("summaryStatus");

    if (!title) return;

    title.textContent = `${identity.name || "Nuovo"} ${identity.surname || "personaggio"}`.trim();
    text.textContent = extra.summary || buildSummary();
    race.textContent = identity.race || "—";
    age.textContent = Number(identity.age) > 0 ? `${identity.age} anni` : "—";
    focus.textContent = getFocus(extra.statistics);
    summaryStatus.textContent = status || (psychology.mental_state ? "Attivo" : "Normale");
    renderLevel();
}

function renderList(rootId, list, type) {
    const root = document.getElementById(rootId);
    if (!root) return;
    root.innerHTML = "";

    if (!list.length) {
        root.innerHTML = '<div class="extra-empty">Nessun elemento presente.</div>';
        return;
    }

    list.forEach((item, index) => {
        const row = document.createElement("div");
        row.className = "extra-item";
        row.innerHTML = `<div><strong>${esc(item.name)}</strong><span>${esc(item.description || "")}</span></div><button type="button" class="danger-button">Rimuovi</button>`;
        row.querySelector("button").addEventListener("click", () => {
            extra[type].splice(index, 1);
            saveExtra();
            renderList(rootId, extra[type], type);
        });
        root.appendChild(row);
    });
}

function addListItem(type, nameId, descriptionId, rootId) {
    const name = document.getElementById(nameId)?.value.trim();
    const description = document.getElementById(descriptionId)?.value.trim();
    if (!name) return;

    extra[type].push({ name, description });
    document.getElementById(nameId).value = "";
    document.getElementById(descriptionId).value = "";
    saveExtra();
    renderList(rootId, extra[type], type);
}

function renderConditions() {
    const map = { conditionHealth:"health", conditionStamina:"stamina", conditionMana:"mana", conditionStatus:"status" };
    Object.entries(map).forEach(([id, key]) => {
        const input = document.getElementById(id);
        if (input) input.value = extra.conditions[key] ?? "";
    });
}

function bindConditions() {
    const map = { conditionHealth:"health", conditionStamina:"stamina", conditionMana:"mana", conditionStatus:"status" };
    Object.entries(map).forEach(([id, key]) => {
        const input = document.getElementById(id);
        if (!input) return;
        input.addEventListener("input", () => {
            extra.conditions[key] = input.type === "number" ? Math.max(0, Number(input.value) || 0) : input.value.trim();
            saveExtra();
        });
    });
}

function generateBaseExtra() {
    const race = (document.getElementById("race")?.value || "").toLowerCase();
    const bias = {
        umano: {charisma:2,luck:2,intelligence:1},
        elfo: {agility:4,intelligence:5,perception:4,constitution:-2},
        nano: {strength:5,constitution:6,agility:-3},
        orco: {strength:7,constitution:5,intelligence:-4,charisma:-2},
        demone: {willpower:5,charisma:4},
        draconide: {strength:4,constitution:5,willpower:3,agility:-2},
        mezzelfo: {agility:3,intelligence:3,charisma:3}
    }[race] || {intelligence:1,charisma:1};

    const pool = [];
    for (let i = 0; i < STAT_NAMES.length; i++) pool.push(Math.floor(Math.random() * 41) + 30);
    pool.sort(() => Math.random() - 0.5);

    const statistics = {};
    STAT_NAMES.forEach((key, index) => {
        statistics[key] = Math.max(5, Math.min(95, pool[index] + (bias[key] || 0) + Math.floor(Math.random() * 13) - 6));
    });

    const maxHealth = 70 + statistics.constitution * 2 + Math.floor(statistics.strength / 2);
    const maxStamina = 50 + statistics.constitution + statistics.agility;
    const maxMana = 20 + statistics.intelligence + statistics.willpower;

    extra = {
        ...cloneDefaultExtra(),
        statistics,
        conditions: { health:maxHealth, stamina:maxStamina, mana:maxMana, status:"Normale" }
    };
    saveExtra();
    renderAll();
}

function setExtra(value) {
    extra = normalizeExtra(value);
    refreshDerivedData();
    saveExtra();
    renderAll();
}

function getExtra() {
    refreshDerivedData();
    return clone(extra);
}

function resetExtra() {
    extra = cloneDefaultExtra();
    saveExtra();
    renderAll();
}

function renderAll() {
    renderStatistics();
    renderList("abilitiesList", extra.abilities, "abilities");
    renderList("skillsList", extra.skills, "skills");
    renderList("relationshipsList", extra.relationships, "relationships");
    renderConditions();
    renderSummary();
}

function initCharacterSections() {
    ["statistics","abilities","skills","conditions","relationships"].forEach(section => {
        document.querySelector(`.nav-button[data-section="${section}"]`)?.classList.remove("disabled");
    });

    document.getElementById("addAbilityButton")?.addEventListener("click", () => addListItem("abilities", "abilityName", "abilityDescription", "abilitiesList"));
    document.getElementById("addSkillButton")?.addEventListener("click", () => addListItem("skills", "skillName", "skillDescription", "skillsList"));
    document.getElementById("addRelationshipButton")?.addEventListener("click", () => addListItem("relationships", "relationshipName", "relationshipDescription", "relationshipsList"));
    document.getElementById("generateBaseStatsButton")?.addEventListener("click", generateBaseExtra);
    document.getElementById("resetExtraButton")?.addEventListener("click", resetExtra);
    bindConditions();
    renderAll();
}

document.addEventListener("DOMContentLoaded", initCharacterSections);

window.aiRpgCharacterSections = {
    reset: resetExtra,
    generateBase: generateBaseExtra,
    render: renderAll,
    getData: getExtra,
    setData: setExtra
};
