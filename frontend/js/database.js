// =========================================================
// AI RPG - CHARACTER DATABASE CLIENT
// =========================================================
//
// Il salvataggio principale viene effettuato dal backend.
// app.js continua a mantenere una copia locale per non perdere
// il lavoro mentre si modifica la scheda.
//
// =========================================================

const CHARACTER_STORAGE_KEY = "ai-rpg-character";
const saveButton = document.getElementById("saveButton");

async function saveCharacterToDatabase() {
    if (!saveButton) return;

    let character;

    try {
        character = JSON.parse(
            localStorage.getItem(CHARACTER_STORAGE_KEY)
        );
    } catch (error) {
        console.error("Personaggio locale non valido:", error);
        alert("Impossibile leggere il personaggio corrente.");
        return;
    }

    if (!character || !character.identity) {
        alert("Non c'è nessun personaggio da salvare.");
        return;
    }

    saveButton.disabled = true;

    try {
        const response = await fetch("/api/characters", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(character)
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                data.error || "Impossibile salvare il personaggio."
            );
        }

        // Il backend assegna l'ID al primo salvataggio.
        // Dai salvataggi successivi verrà usato per UPDATE.
        character.id = data.id;

        if (data.identity) {
            character.identity = {
                ...character.identity,
                ...data.identity
            };
        }

        localStorage.setItem(
            CHARACTER_STORAGE_KEY,
            JSON.stringify(character)
        );

        alert(
            character.id
                ? `Personaggio salvato. ID: ${character.id}`
                : "Personaggio salvato."
        );

    } catch (error) {
        console.error("Errore salvataggio database:", error);
        alert(
            "Impossibile salvare il personaggio nel database.\n\n" +
            error.message
        );
    } finally {
        saveButton.disabled = false;
    }
}

// Intercettiamo il click prima del vecchio handler di app.js.
// In questo modo il pulsante Salva usa realmente il database.
if (saveButton) {
    saveButton.addEventListener(
        "click",
        event => {
            event.preventDefault();
            event.stopImmediatePropagation();
            saveCharacterToDatabase();
        },
        true
    );
}
