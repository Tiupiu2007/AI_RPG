export const STORAGE_KEY = "ai-rpg-character";
export const EXTRA_STORAGE_KEY = "ai-rpg-character-extra";

export function createEmptyCharacter() {
    return {
        identity: { name:"", surname:"", nickname:"", age:0, birth_date:"", sex:"", race:"", physical_description:"", appearance:"" },
        languages: [],
        psychology: { mental_state:"", emotional_stability:"", fears:"", desires:"", values:"", traumas:"" },
        personality: { personality_description:"", traits:"", strengths:"", flaws:"", habits:"", social_behavior:"" },
        extra: { statistics:{}, abilities:[], skills:[], conditions:{health:0,stamina:0,mana:0,status:"Normale"}, relationships:[] }
    };
}

export function normalizeCharacter(value) {
    const empty = createEmptyCharacter();
    if (!value || typeof value !== "object") return empty;
    const identity = value.identity || {};
    const psychology = value.psychology || {};
    const personality = value.personality || {};
    const extra = value.extra || {};
    return {
        id: value.id,
        identity: { ...empty.identity, ...identity, age:Number.isFinite(Number(identity.age)) ? Number(identity.age) : 0 },
        languages: Array.isArray(value.languages) ? value.languages : [],
        psychology: { ...empty.psychology, ...psychology },
        personality: { ...empty.personality, ...personality },
        extra: { ...empty.extra, ...extra, statistics:{...empty.extra.statistics,...(extra.statistics||{})}, conditions:{...empty.extra.conditions,...(extra.conditions||{})}, abilities:Array.isArray(extra.abilities)?extra.abilities:[], skills:Array.isArray(extra.skills)?extra.skills:[], relationships:Array.isArray(extra.relationships)?extra.relationships:[] }
    };
}

export function loadLocalCharacter() {
    try { return normalizeCharacter(JSON.parse(localStorage.getItem(STORAGE_KEY))); }
    catch { return createEmptyCharacter(); }
}

export function saveLocalCharacter(character) {
    if (character) localStorage.setItem(STORAGE_KEY, JSON.stringify(character));
}

export function clearLocalCharacter() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(EXTRA_STORAGE_KEY);
}
