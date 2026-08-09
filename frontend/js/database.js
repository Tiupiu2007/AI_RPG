// =========================================================
// AI RPG - CHARACTER DATABASE CLIENT
// =========================================================

const CHARACTER_STORAGE_KEY = "ai-rpg-character";
const saveButton = document.getElementById("saveButton");
const characterList = document.getElementById("characterList");

function getLocalCharacter() {
    try {
        return JSON.parse(localStorage.getItem(CHARACTER_STORAGE_KEY));
    } catch {
        return null;
    }
}

function setLocalCharacter(character) {
    localStorage.setItem(CHARACTER_STORAGE_KEY, JSON.stringify(character));
}

async function saveCharacterToDatabase() {
    const character = getLocalCharacter();
    if (!character || !character.identity) {
        alert("Non c'è nessun personaggio da salvare.");
        return;
    }

    saveButton.disabled = true;
    try {
        const response = await fetch("/api/characters", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(character)
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.error || "Impossibile salvare il personaggio.");
        }

        character.id = data.id;
        if (data.identity) character.identity = { ...character.identity, ...data.identity };
        setLocalCharacter(character);
        await loadCharacterList();
        alert(`Personaggio salvato. ID: ${character.id}`);
    } catch (error) {
        console.error("Errore salvataggio database:", error);
        alert("Impossibile salvare il personaggio nel database.\n\n" + error.message);
    } finally {
        saveButton.disabled = false;
    }
}

async function loadCharacterList() {
    if (!characterList) return;

    try {
        const response = await fetch("/api/characters");
        const characters = await response.json();
        if (!response.ok) throw new Error(characters.error || "Impossibile caricare i personaggi.");

        characterList.innerHTML = "";
        if (!characters.length) {
            const empty = document.createElement("div");
            empty.className = "character-list-empty";
            empty.textContent = "Nessun personaggio salvato.";
            characterList.appendChild(empty);
            return;
        }

        const current = getLocalCharacter();
        characters.forEach(entry => {
            const identity = entry.identity || {};
            const fullName = `${identity.name || "Senza nome"} ${identity.surname || ""}`.trim();
            const row = document.createElement("div");
            row.className = "character-entry";

            const loadButton = document.createElement("button");
            loadButton.className = "character-load";
            if (current && Number(current.id) === Number(entry.id)) loadButton.classList.add("current");
            loadButton.textContent = fullName || `Personaggio #${entry.id}`;
            loadButton.title = `ID ${entry.id}`;
            loadButton.addEventListener("click", () => loadCharacterFromDatabase(entry.id));

            const deleteButton = document.createElement("button");
            deleteButton.className = "character-delete";
            deleteButton.textContent = "×";
            deleteButton.title = "Elimina personaggio";
            deleteButton.addEventListener("click", event => {
                event.stopPropagation();
                deleteCharacterFromDatabase(entry.id, fullName);
            });

            row.append(loadButton, deleteButton);
            characterList.appendChild(row);
        });
    } catch (error) {
        console.error("Errore caricamento personaggi:", error);
        characterList.innerHTML = "";
        const element = document.createElement("div");
        element.className = "character-list-empty";
        element.textContent = "Impossibile caricare i personaggi.";
        characterList.appendChild(element);
    }
}

async function loadCharacterFromDatabase(characterId) {
    try {
        const response = await fetch(`/api/characters/${characterId}`);
        const character = await response.json();
        if (!response.ok) throw new Error(character.error || "Personaggio non trovato.");
        setLocalCharacter(character);
        window.location.reload();
    } catch (error) {
        console.error("Errore caricamento personaggio:", error);
        alert("Impossibile caricare il personaggio.\n\n" + error.message);
    }
}

async function deleteCharacterFromDatabase(characterId, name) {
    if (!confirm(`Eliminare definitivamente "${name}"?`)) return;

    try {
        const response = await fetch(`/api/characters/${characterId}`, { method: "DELETE" });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Impossibile eliminare il personaggio.");

        const current = getLocalCharacter();
        if (current && Number(current.id) === Number(characterId)) {
            localStorage.removeItem(CHARACTER_STORAGE_KEY);
            window.location.reload();
            return;
        }
        await loadCharacterList();
    } catch (error) {
        console.error("Errore eliminazione personaggio:", error);
        alert("Impossibile eliminare il personaggio.\n\n" + error.message);
    }
}

// Il salvataggio definitivo resta centralizzato nel modulo database.
if (saveButton) {
    saveButton.addEventListener("click", event => {
        event.preventDefault();
        event.stopImmediatePropagation();
        saveCharacterToDatabase();
    }, true);
}

loadCharacterList();
