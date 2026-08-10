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
const CHARACTER_INTERACTION_ENDPOINT = "/api/character-interaction";

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
                <p>Modalità di test: parla con il personaggio attraverso il backend del gioco.</p>
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

    if (!character || !character.id) {
        chatElement.innerHTML = '<div class="chat-empty">Seleziona o salva un personaggio prima di iniziare una conversazione.</div>';
        return;
    }

    const messages = loadChat(character);
    if (!messages.length) {
        chatElement.innerHTML = '<div class="chat-empty">Questa modalità usa il backend del gioco: il personaggio viene recuperato dal database e la risposta passa dal controller AI.</div>';
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
    if (!character?.id || !input || !sendButton) return;

    const text = input.value.trim();
    if (!text) return;

    const messages = loadChat(character);
    messages.push({ role: "user", content: text });
    saveChat(character, messages);
    input.value = "";
    renderInteraction();

    sendButton.disabled = true;
    setInteractionStatus("Il game engine sta elaborando il turno...");

    try {
        const response = await fetch(CHARACTER_INTERACTION_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                character_id: Number(character.id),
                message: text,
                recent_conversation: messages.slice(-16),
            }),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || `Backend HTTP ${response.status}`);
        }

        const reply = String(data.narration || "").trim();
        if (!reply) {
            throw new Error("Il game engine non ha prodotto una risposta narrativa.");
        }

        messages.push({ role: "assistant", content: reply });
        saveChat(character, messages);
        renderInteraction();
        setInteractionStatus("Turno completato.");
    } catch (error) {
        messages.pop();
        saveChat(character, messages);
        renderInteraction();
        setInteractionStatus(`Errore backend: ${error.message}`);
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
