// =========================================================
// AI RPG - CHARACTER DESCRIPTION UI
// =========================================================

export function initializeCharacterDescriptionUI() {
    const input = document.getElementById("characterDescription");
    if (!input) return;

    document.getElementById("clearCharacterDescription")?.addEventListener("click", () => {
        input.value = "";
        input.focus();
    });

    document.getElementById("generateFromDescriptionButton")?.addEventListener("click", () => {
        const description = String(input.value || "").trim();

        if (!description) {
            input.focus();
            alert("Scrivi prima una breve descrizione del personaggio.");
            return;
        }

        window.dispatchEvent(new CustomEvent("ai-rpg-generate-character", {
            detail: { description, source: "manual", importance: "major" }
        }));
    });
}

// =========================================================
// AI RPG - CHARACTER INTERACTION TEST PANEL
// =========================================================

const INTERACTION_STORAGE_PREFIX = "ai-rpg-character-chat:";
const OLLAMA_URL = "http://127.0.0.1:11434/api/chat";
const OLLAMA_MODEL = "qwen3:8b";

function getCurrentCharacter() {
    try {
        const character = JSON.parse(localStorage.getItem("ai-rpg-character"));
        return character && typeof character === "object" ? character : null;
    } catch {
        return null;
    }
}

function characterChatKey(character) {
    return `${INTERACTION_STORAGE_PREFIX}${character?.id ?? `${character?.identity?.name ?? "unknown"}:${character?.identity?.surname ?? ""}`}`;
}

function loadChat(character) {
    try {
        const value = JSON.parse(localStorage.getItem(characterChatKey(character)));
        return Array.isArray(value) ? value : [];
    } catch {
        return [];
    }
}

function saveChat(character, messages) {
    localStorage.setItem(characterChatKey(character), JSON.stringify(messages));
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>\"]/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"
    }[char]));
}

function buildCharacterContext(character) {
    const identity = character?.identity || {};
    const psychology = character?.psychology || {};
    const personality = character?.personality || {};
    const extra = character?.extra || {};

    return JSON.stringify({
        identity,
        psychology,
        personality,
        statistics: extra.statistics || {},
        abilities: extra.abilities || [],
        skills: extra.skills || [],
        conditions: extra.conditions || {},
        relationships: extra.relationships || [],
        inventory: extra.inventory || {},
        magic: extra.magic || {},
    }, null, 2);
}

function ensureInteractionUI() {
    const nav = document.querySelector(".sidebar nav");
    const content = document.getElementById("content");
    if (!nav || !content || document.getElementById("interactionSection")) return;

    const button = document.createElement("button");
    button.className = "nav-button";
    button.dataset.section = "interaction";
    button.innerHTML = '<span class="nav-number">12</span>Interazione';
    nav.appendChild(button);

    const section = document.createElement("div");
    section.id = "interactionSection";
    section.className = "section hidden";
    section.innerHTML = `
        <div class="section-header">
            <div>
                <span class="section-number">12</span>
                <h2>Interazione</h2>
                <p>Modalità di test: parla direttamente con il personaggio selezionato.</p>
            </div>
        </div>
        <div class="card character-interaction-card">
            <div class="interaction-character-bar">
                <div>
                    <div class="interaction-label">PERSONAGGIO SELEZIONATO</div>
                    <strong id="interactionCharacterName">Nessun personaggio</strong>
                </div>
                <button id="clearCharacterChat" type="button" class="secondary-button">Pulisci chat</button>
            </div>
            <div id="characterChat" class="character-chat"></div>
            <div class="character-chat-input-row">
                <textarea id="characterChatInput" class="character-chat-input" rows="2" placeholder="Scrivi qualcosa al personaggio..."></textarea>
                <button id="sendCharacterMessage" type="button" class="primary-button">Invia ➤</button>
            </div>
            <div id="characterChatStatus" class="character-chat-status">Pronto.</div>
        </div>
    `;
    content.appendChild(section);

    button.addEventListener("click", () => {
        document.querySelectorAll(".section").forEach(item => item.classList.add("hidden"));
        section.classList.remove("hidden");
        document.querySelectorAll(".nav-button").forEach(item => item.classList.toggle("active", item === button));
        renderInteraction();
    });

    document.getElementById("clearCharacterChat")?.addEventListener("click", clearCharacterChat);
    document.getElementById("sendCharacterMessage")?.addEventListener("click", sendCharacterMessage);
    document.getElementById("characterChatInput")?.addEventListener("keydown", event => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendCharacterMessage();
        }
    });

    injectInteractionStyles();
    renderInteraction();
}

function injectInteractionStyles() {
    if (document.getElementById("characterInteractionStyles")) return;
    const style = document.createElement("style");
    style.id = "characterInteractionStyles";
    style.textContent = `
        .character-interaction-card { padding: 0; overflow: hidden; }
        .interaction-character-bar { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:18px 20px; border-bottom:1px solid var(--border); background:var(--surface-2); }
        .interaction-label { margin-bottom:4px; color:var(--muted); font-size:9px; font-weight:700; letter-spacing:1.5px; }
        .interaction-character-bar strong { font-size:15px; }
        .character-chat { min-height:430px; max-height:58vh; overflow-y:auto; padding:22px; display:flex; flex-direction:column; gap:14px; background:#0d0f11; }
        .chat-message { max-width:78%; padding:11px 14px; border:1px solid var(--border); border-radius:12px; line-height:1.55; font-size:13px; white-space:pre-wrap; }
        .chat-message.character { align-self:flex-start; background:var(--surface-2); }
        .chat-message.player { align-self:flex-end; background:var(--surface-3); }
        .chat-message-meta { margin-bottom:5px; color:var(--muted); font-size:9px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }
        .chat-empty { margin:auto; max-width:420px; color:var(--muted); text-align:center; font-size:12px; line-height:1.6; }
        .character-chat-input-row { display:flex; gap:10px; padding:14px; border-top:1px solid var(--border); background:var(--surface); }
        .character-chat-input { flex:1; min-height:48px; max-height:160px; resize:vertical; }
        .character-chat-input-row .primary-button { align-self:flex-end; min-width:100px; }
        .character-chat-status { padding:0 16px 13px; color:var(--muted); font-size:10px; }
        @media(max-width:700px){ .interaction-character-bar,.character-chat-input-row{flex-direction:column;align-items:stretch}.chat-message{max-width:92%}.character-chat{min-height:360px} }
    `;
    document.head.appendChild(style);
}

function renderInteraction() {
    const character = getCurrentCharacter();
    const nameElement = document.getElementById("interactionCharacterName");
    const chatElement = document.getElementById("characterChat");
    if (!nameElement || !chatElement) return;

    const name = `${character?.identity?.name || ""} ${character?.identity?.surname || ""}`.trim();
    nameElement.textContent = name || "Nessun personaggio";

    if (!character) {
        chatElement.innerHTML = '<div class="chat-empty">Seleziona o genera un personaggio prima di iniziare una conversazione.</div>';
        return;
    }

    const messages = loadChat(character);
    if (!messages.length) {
        chatElement.innerHTML = '<div class="chat-empty">Questa è una modalità di test. Scrivi qualcosa: il personaggio risponderà usando i propri dati e la propria personalità.</div>';
        return;
    }

    chatElement.innerHTML = messages.map(message => `
        <div class="chat-message ${message.role === "user" ? "player" : "character"}">
            <div class="chat-message-meta">${message.role === "user" ? "Tu" : escapeHtml(name || "Personaggio")}</div>
            ${escapeHtml(message.content)}
        </div>
    `).join("");
    chatElement.scrollTop = chatElement.scrollHeight;
}

function setInteractionStatus(text) {
    const status = document.getElementById("characterChatStatus");
    if (status) status.textContent = text;
}

async function sendCharacterMessage() {
    const character = getCurrentCharacter();
    const input = document.getElementById("characterChatInput");
    const sendButton = document.getElementById("sendCharacterMessage");
    if (!character || !input || !sendButton) return;

    const text = input.value.trim();
    if (!text) return;

    const messages = loadChat(character);
    messages.push({ role: "user", content: text });
    saveChat(character, messages);
    input.value = "";
    renderInteraction();

    sendButton.disabled = true;
    setInteractionStatus("Il personaggio sta pensando...");

    const identity = character.identity || {};
    const characterName = `${identity.name || "Personaggio"} ${identity.surname || ""}`.trim();
    const systemPrompt = `Sei ${characterName}. Devi interpretare esclusivamente questo personaggio.

Regole:
- Rispondi in italiano.
- Parla e ragiona coerentemente con personalità, psicologia, storia e conoscenze del personaggio.
- Non conoscere informazioni che il personaggio non possiede.
- Non controllare il giocatore.
- Non inventare improvvisamente poteri, ricordi o informazioni incompatibili con il profilo.
- Rispondi naturalmente, come in una conversazione reale.
- Non descrivere il funzionamento dell'IA e non parlare come narratore.

DATI DEL PERSONAGGIO:
${buildCharacterContext(character)}`;

    try {
        const response = await fetch(OLLAMA_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                model: OLLAMA_MODEL,
                stream: false,
                messages: [{ role: "system", content: systemPrompt }, ...messages.slice(-16)],
                options: { temperature: 0.8 },
            }),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Ollama non ha accettato la richiesta.");
        const reply = String(data?.message?.content || "").trim();
        if (!reply) throw new Error("Il personaggio non ha restituito una risposta.");

        messages.push({ role: "assistant", content: reply });
        saveChat(character, messages);
        renderInteraction();
        setInteractionStatus("Pronto.");
    } catch (error) {
        messages.pop();
        saveChat(character, messages);
        renderInteraction();
        setInteractionStatus(`Errore: ${error.message}. Assicurati che Ollama sia attivo e che il modello ${OLLAMA_MODEL} sia disponibile.`);
    } finally {
        sendButton.disabled = false;
        input.focus();
    }
}

function clearCharacterChat() {
    const character = getCurrentCharacter();
    if (!character) return;
    localStorage.removeItem(characterChatKey(character));
    renderInteraction();
    setInteractionStatus("Chat pulita.");
}

window.addEventListener("ai-rpg-character-changed", renderInteraction);
window.addEventListener("storage", renderInteraction);

document.addEventListener("DOMContentLoaded", () => {
    initializeCharacterDescriptionUI();
    ensureInteractionUI();
});
