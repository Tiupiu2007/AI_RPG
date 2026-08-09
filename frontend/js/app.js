// =========================================================
// AI RPG - CHARACTER EDITOR
// =========================================================

let character = null;
let availableRaces = [];
let availableLanguages = [];

const STORAGE_KEY = "ai-rpg-character";
const PROFILE_FIELDS = ["mentalState","emotionalStability","fears","desires","values","traumas","personalityDescription","traits","strengths","flaws","habits","socialBehavior"];

const generateButton = document.getElementById("generateButton");
const newCharacterButton = document.getElementById("newCharacterButton");
const saveButton = document.getElementById("saveButton");
const overlay = document.getElementById("generationOverlay");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const generationStatus = document.getElementById("generationStatus");
const generationName = document.getElementById("generationName");

const inputs = {
    name: document.getElementById("name"), surname: document.getElementById("surname"),
    nickname: document.getElementById("nickname"), age: document.getElementById("age"),
    birthDate: document.getElementById("birthDate"), sex: document.getElementById("sex"),
    race: document.getElementById("race"), physicalDescription: document.getElementById("physicalDescription"),
    appearance: document.getElementById("appearance")
};

function createEmptyCharacter() {
    return {
        identity: { name:"", surname:"", nickname:"", age:0, birth_date:"", sex:"", race:"", physical_description:"", appearance:"" },
        languages: [],
        psychology: { mental_state:"", emotional_stability:"", fears:"", desires:"", values:"", traumas:"" },
        personality: { personality_description:"", traits:"", strengths:"", flaws:"", habits:"", social_behavior:"" },
        extra: { statistics:{}, abilities:[], skills:[], conditions:{health:0,stamina:0,mana:0,status:"Normale"}, relationships:[] }
    };
}

function normalizeCharacter(value) {
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
        extra: { ...empty.extra, ...extra, statistics:{...(empty.extra.statistics),...(extra.statistics||{})}, conditions:{...empty.extra.conditions,...(extra.conditions||{})}, abilities:Array.isArray(extra.abilities)?extra.abilities:[], skills:Array.isArray(extra.skills)?extra.skills:[], relationships:Array.isArray(extra.relationships)?extra.relationships:[] }
    };
}

async function loadWorldData() {
    const racesResponse = await fetch("/api/races");
    if (!racesResponse.ok) throw new Error("Impossibile caricare le razze.");
    availableRaces = await racesResponse.json();
    const languagesResponse = await fetch("/api/languages");
    if (!languagesResponse.ok) throw new Error("Impossibile caricare le lingue.");
    availableLanguages = await languagesResponse.json();
}

function findRace(name) { return availableRaces.find(r => String(r.name).trim().toLowerCase() === String(name||"").trim().toLowerCase()) || null; }
function findLanguage(name) { return availableLanguages.find(l => String(l.name).trim().toLowerCase() === String(name||"").trim().toLowerCase()) || null; }

function initializeNavigation() {
    document.querySelectorAll(".nav-button").forEach(button => button.addEventListener("click", () => {
        if (button.classList.contains("disabled")) return;
        const section = button.dataset.section;
        if (!section) return;
        activateSection(section);
    }));
}
function showSection(section) { document.querySelectorAll(".section").forEach(e => e.classList.add("hidden")); document.getElementById(`${section}Section`)?.classList.remove("hidden"); }
function activateSection(section) { showSection(section); document.querySelectorAll(".nav-button").forEach(b => b.classList.toggle("active", b.dataset.section === section)); }

function initializeRaceSelector() {
    if (!inputs.race || inputs.race.tagName.toLowerCase() !== "select") return;
    inputs.race.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = ""; placeholder.textContent = "Seleziona razza"; placeholder.disabled = true;
    inputs.race.appendChild(placeholder);
    availableRaces.forEach(race => { const option=document.createElement("option"); option.value=race.name; option.textContent=race.name; inputs.race.appendChild(option); });
    inputs.race.addEventListener("change", handleRaceChange);
}

async function handleRaceChange() {
    if (!character) return;
    const race = findRace(inputs.race.value.trim());
    if (!race) return;
    character.identity.race = race.name;
    try {
        const response = await fetch("/api/race-languages", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({race:race.name}) });
        if (!response.ok) throw new Error("Impossibile caricare le lingue della razza.");
        character.languages = await response.json();
    } catch(error) { console.error(error); character.languages=[]; }
    loadLanguages(); saveLocalCharacter(); updateCharacterTitle();
}

function loadCharacter() {
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch(error) { console.warn("Salvataggio locale non valido.", error); }
    character = normalizeCharacter(saved);
    loadCharacterIntoUI();
}

function loadCharacterIntoUI() {
    const identity = character.identity;
    inputs.name.value=identity.name||""; inputs.surname.value=identity.surname||""; inputs.nickname.value=identity.nickname||"";
    inputs.age.value=identity.age??0; inputs.birthDate.value=identity.birth_date||""; inputs.sex.value=identity.sex||"";
    inputs.race.value=identity.race||""; inputs.physicalDescription.value=identity.physical_description||""; inputs.appearance.value=identity.appearance||"";
    PROFILE_FIELDS.forEach(field => { const input=document.getElementById(field); if(input) input.value=getProfileValue(field)||""; });
    loadLanguages(); updateCharacterTitle();
    if (window.aiRpgCharacterSections?.setData) window.aiRpgCharacterSections.setData(character.extra);
}

function getProfileValue(field) {
    const p={mentalState:"mental_state",emotionalStability:"emotional_stability",fears:"fears",desires:"desires",values:"values",traumas:"traumas"};
    const q={personalityDescription:"personality_description",traits:"traits",strengths:"strengths",flaws:"flaws",habits:"habits",socialBehavior:"social_behavior"};
    return p[field] ? character.psychology[p[field]] : q[field] ? character.personality[q[field]] : "";
}
function updateProfileFromUI() {
    const p={mentalState:"mental_state",emotionalStability:"emotional_stability",fears:"fears",desires:"desires",values:"values",traumas:"traumas"};
    const q={personalityDescription:"personality_description",traits:"traits",strengths:"strengths",flaws:"flaws",habits:"habits",socialBehavior:"social_behavior"};
    PROFILE_FIELDS.forEach(field=>{const input=document.getElementById(field);if(!input)return;if(p[field])character.psychology[p[field]]=input.value.trim();if(q[field])character.personality[q[field]]=input.value.trim();});
}

function loadLanguages() {
    const list=document.getElementById("languagesList"); if(!list)return; list.innerHTML="";
    if(!character.languages.length){const empty=document.createElement("div");empty.className="empty-language";empty.textContent="Nessuna lingua conosciuta.";list.appendChild(empty);return;}
    character.languages.forEach(language=>{const item=document.createElement("div");item.className="language-item";const name=document.createElement("div");name.className="language-name";name.textContent=language.name||"Lingua sconosciuta";item.appendChild(name);const levels=document.createElement("div");levels.className="language-level-values";addLanguageLevel(levels,"Comprensione",language.comprehension);addLanguageLevel(levels,"Parlato",language.speaking);addLanguageLevel(levels,"Scrittura",language.writing);item.appendChild(levels);list.appendChild(item);});
}
function addLanguageLevel(container,label,value){const row=document.createElement("div");row.className="language-value-row";const text=document.createElement("span");text.textContent=label;const valueText=document.createElement("span");valueText.textContent=`${Math.round(Number(value||0)*100)}%`;row.appendChild(text);row.appendChild(valueText);container.appendChild(row);}

function updateCharacterFromUI() {
    if(!character)return;
    character.identity.name=inputs.name.value.trim();character.identity.surname=inputs.surname.value.trim();character.identity.nickname=inputs.nickname.value.trim();character.identity.age=Number(inputs.age.value)||0;character.identity.birth_date=inputs.birthDate.value.trim();character.identity.sex=inputs.sex.value.trim();character.identity.race=inputs.race.value.trim();character.identity.physical_description=inputs.physicalDescription.value.trim();character.identity.appearance=inputs.appearance.value.trim();
    updateProfileFromUI();
    if(window.aiRpgCharacterSections?.getData) character.extra=window.aiRpgCharacterSections.getData();
    saveLocalCharacter();updateCharacterTitle();
}
function initializeInputListeners(){Object.values(inputs).forEach(input=>input?.addEventListener("input",updateCharacterFromUI));PROFILE_FIELDS.forEach(field=>document.getElementById(field)?.addEventListener("input",updateCharacterFromUI));}
function updateCharacterTitle(){const title=document.getElementById("characterTitle");if(!title||!character)return;title.textContent=`${character.identity.name||""} ${character.identity.surname||""}`.trim()||"Nuovo personaggio";}

function newCharacter(){
    if(!confirm("Creare un nuovo personaggio? Le modifiche non salvate verranno perse."))return;
    character=createEmptyCharacter();localStorage.removeItem(STORAGE_KEY);localStorage.removeItem("ai-rpg-character-extra");loadCharacterIntoUI();activateSection("identity");
}
function saveLocalCharacter(){if(!character)return;localStorage.setItem(STORAGE_KEY,JSON.stringify(character));}

async function persistCharacterToDatabase() {
    updateCharacterFromUI();
    const response=await fetch("/api/characters",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(character)});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.error||"Salvataggio sul database fallito.");
    character.id=data.id;saveLocalCharacter();
    return data;
}

async function saveCharacter(){try{await persistCharacterToDatabase();alert(`Personaggio salvato. ID: ${character.id}`);}catch(error){console.error(error);saveLocalCharacter();alert(`Salvataggio locale eseguito, ma database non aggiornato.\n\n${error.message}`);}}

async function generateCharacter(){
    if(generateButton.disabled)return;
    generateButton.disabled=true;newCharacterButton.disabled=true;overlay.classList.remove("hidden");resetGeneration();
    try{
        setGenerationStep("stepRace","active");setProgress(10,"Scelta della razza e generazione del personaggio...");
        const response=await fetch("/api/generate-character",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
        const generated=await response.json().catch(()=>({}));
        if(!response.ok)throw new Error(generated.error||"Generazione fallita.");
        setGenerationStep("stepRace","completed");setGenerationStep("stepIdentity","active");setProgress(30,"Identità, corpo e aspetto generati...");await wait(120);setGenerationStep("stepIdentity","completed");
        setGenerationStep("stepLanguages","active");setProgress(45,"Lingue assegnate in base alla razza...");await wait(120);setGenerationStep("stepLanguages","completed");
        setGenerationStep("stepAppearance","active");setProgress(60,"Statistiche personali e stato iniziale...");await wait(120);setGenerationStep("stepAppearance","completed");
        setGenerationStep("stepConsistency","active");setProgress(78,"Psicologia, personalità, abilità e skill...");
        character=normalizeCharacter(generated);loadCharacterIntoUI();saveLocalCharacter();await wait(150);setGenerationStep("stepConsistency","completed");
        setGenerationStep("stepComplete","active");setProgress(92,"Salvataggio completo nel database...");
        await persistCharacterToDatabase();
        setGenerationStep("stepComplete","completed");setProgress(100,"Personaggio completato e salvato.");generationName.textContent=`${character.identity.name} ${character.identity.surname}`.trim();
        await wait(700);overlay.classList.add("hidden");activateSection("identity");
    }catch(error){console.error("Errore durante la generazione:",error);generationName.textContent="Generazione fallita";setProgress(100,error.message);alert(`Non è stato possibile generare il personaggio.\n\n${error.message}`);await wait(700);overlay.classList.add("hidden");}
    finally{generateButton.disabled=false;newCharacterButton.disabled=false;}
}

function resetGeneration(){setProgress(0,"L'IA sta preparando il personaggio...");generationName.textContent="Generazione in corso...";["stepRace","stepIdentity","stepLanguages","stepAppearance","stepConsistency","stepComplete"].forEach(id=>{const e=document.getElementById(id);if(!e)return;e.classList.remove("active","completed");const s=e.querySelector("span");if(s)s.textContent="○";});}
function setProgress(value,status){if(progressBar)progressBar.style.width=`${value}%`;if(progressText)progressText.textContent=`${value}%`;if(generationStatus)generationStatus.textContent=status;}
function setGenerationStep(id,state){const e=document.getElementById(id);if(!e)return;e.classList.remove("active","completed");const s=e.querySelector("span");if(state==="active"){e.classList.add("active");if(s)s.textContent="◉";}if(state==="completed"){e.classList.add("completed");if(s)s.textContent="✓";}}
function wait(milliseconds){return new Promise(resolve=>setTimeout(resolve,milliseconds));}

function initializeEvents(){generateButton?.addEventListener("click",generateCharacter);newCharacterButton?.addEventListener("click",newCharacter);saveButton?.addEventListener("click",saveCharacter);}
async function initializeApp(){try{await loadWorldData();initializeNavigation();initializeRaceSelector();initializeInputListeners();initializeEvents();loadCharacter();}catch(error){console.error("Errore avvio interfaccia:",error);alert(`Impossibile avviare l'interfaccia.\n\n${error.message}`);}}
initializeApp();
