const aSelect = document.getElementById("characterA");
const bSelect = document.getElementById("characterB");
const simulateButton = document.getElementById("simulateButton");
const clearButton = document.getElementById("clearButton");
const status = document.getElementById("status");
const arena = document.getElementById("arena");

function option(character) {
    const identity = character.identity || {};
    const name = [identity.name, identity.surname].filter(Boolean).join(" ") || `Personaggio ${character.id}`;
    const opt = document.createElement("option");
    opt.value = character.id;
    opt.textContent = name;
    return opt;
}

async function loadCharacters() {
    try {
        const response = await fetch("/api/characters");
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Impossibile caricare i personaggi.");
        for (const character of Array.isArray(data) ? data : []) {
            aSelect.appendChild(option(character));
            bSelect.appendChild(option(character));
        }
        status.textContent = "Seleziona due personaggi.";
    } catch (error) {
        status.textContent = error.message;
    }
}

function clearArena() {
    arena.textContent = "";
    arena.classList.add("hidden");
    status.textContent = "Seleziona due personaggi.";
}

async function simulate() {
    const characterA = Number(aSelect.value);
    const characterB = Number(bSelect.value);
    if (!characterA || !characterB) return (status.textContent = "Seleziona entrambi i personaggi.");
    if (characterA === characterB) return (status.textContent = "Seleziona due personaggi diversi.");

    simulateButton.disabled = true;
    status.textContent = "L'IA sta simulando lo scontro...";
    arena.classList.remove("hidden");
    arena.textContent = "Preparazione dello scontro...";

    try {
        const response = await fetch("/api/combat/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ character_a_id: characterA, character_b_id: characterB })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Simulazione fallita.");
        arena.textContent = data.narration || data.summary || "Nessun risultato.";
        status.textContent = data.winner_name ? `Vincitore: ${data.winner_name}` : "Scontro completato.";
    } catch (error) {
        arena.textContent = "";
        arena.classList.add("hidden");
        status.textContent = error.message;
    } finally {
        simulateButton.disabled = false;
    }
}

simulateButton.addEventListener("click", simulate);
clearButton.addEventListener("click", clearArena);
loadCharacters();
