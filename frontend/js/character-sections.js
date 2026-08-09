const EXTRA_KEY = "ai-rpg-character-extra";
const STAT_NAMES = ["strength","constitution","agility","intelligence","perception","willpower","charisma","luck"];
const DEFAULT_EXTRA = {
    statistics: Object.fromEntries(STAT_NAMES.map(name => [name, 10])),
    abilities: [],
    skills: [],
    conditions: { health: 100, stamina: 100, mana: 0, status: "Normale" },
    relationships: []
};

let extra = loadExtra();

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function cloneDefaultExtra() { return clone(DEFAULT_EXTRA); }

function loadExtra() {
    try {
        const local = JSON.parse(localStorage.getItem(EXTRA_KEY));
        return normalizeExtra(local);
    } catch (_) {
        return cloneDefaultExtra();
    }
}

function normalizeExtra(value) {
    const base = cloneDefaultExtra();
    if (!value || typeof value !== "object") return base;
    return {
        statistics: { ...base.statistics, ...(value.statistics || {}) },
        abilities: Array.isArray(value.abilities) ? value.abilities : [],
        skills: Array.isArray(value.skills) ? value.skills : [],
        conditions: { ...base.conditions, ...(value.conditions || {}) },
        relationships: Array.isArray(value.relationships) ? value.relationships : []
    };
}

function saveExtra() {
    localStorage.setItem(EXTRA_KEY, JSON.stringify(extra));
    syncWithCharacterStorage();
}

function syncWithCharacterStorage() {
    try {
        const character = JSON.parse(localStorage.getItem("ai-rpg-character"));
        if (!character || typeof character !== "object") return;
        character.extra = { ...(character.extra || {}), ...clone(extra) };
        localStorage.setItem("ai-rpg-character", JSON.stringify(character));
    } catch (_) {}
}

function esc(value) {
    return String(value ?? "").replace(/[&<>\"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
}

function labelForStat(key) {
    return {
        strength: "Forza", constitution: "Costituzione", agility: "Agilità",
        intelligence: "Intelligenza", perception: "Percezione", willpower: "Volontà",
        charisma: "Carisma", luck: "Fortuna"
    }[key] || key;
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
        });
    });
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
    const map = {
        conditionHealth: "health", conditionStamina: "stamina",
        conditionMana: "mana", conditionStatus: "status"
    };
    Object.entries(map).forEach(([id, key]) => {
        const input = document.getElementById(id);
        if (input) input.value = extra.conditions[key] ?? "";
    });
}

function bindConditions() {
    const map = {
        conditionHealth: "health", conditionStamina: "stamina",
        conditionMana: "mana", conditionStatus: "status"
    };
    Object.entries(map).forEach(([id, key]) => {
        const input = document.getElementById(id);
        if (!input) return;
        input.addEventListener("input", () => {
            extra.conditions[key] = input.type === "number"
                ? Math.max(0, Number(input.value) || 0)
                : input.value.trim();
            saveExtra();
        });
    });
}

function generateBaseExtra() {
    const race = (document.getElementById("race")?.value || "").toLowerCase();
    const bias = {
        elfo: {agility:4,intelligence:5,perception:4,constitution:-2},
        nano: {strength:5,constitution:6,agility:-3},
        orco: {strength:7,constitution:5,intelligence:-4,charisma:-2},
        demone: {willpower:5,charisma:4},
        draconide: {strength:4,constitution:5,willpower:3,agility:-2},
        mezzelfo: {agility:3,intelligence:3,charisma:3}
    }[race] || {intelligence:1, charisma:1};

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
        conditions: { health: maxHealth, stamina: maxStamina, mana: maxMana, status: "Normale" }
    };
    saveExtra();
    renderAll();
}

function setExtra(value) {
    extra = normalizeExtra(value);
    saveExtra();
    renderAll();
}

function getExtra() {
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
