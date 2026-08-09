// =========================================================
// AI RPG - CHARACTER DESCRIPTION UI
// =========================================================

export function initializeCharacterDescriptionUI() {
    const identitySection = document.getElementById("identitySection");
    if (!identitySection || document.getElementById("characterDescription")) return;

    const firstCard = identitySection.querySelector(".card");
    if (!firstCard) return;

    const card = document.createElement("div");
    card.className = "card character-description-card";
    card.innerHTML = `
        <div class="card-title">Descrizione di partenza</div>
        <p class="description-hint">
            Scrivi una breve descrizione del personaggio. Puoi indicare solo le idee principali:
            età, aspetto, carattere, passato, capacità o qualsiasi dettaglio importante.
            Il sistema completerà automaticamente tutto il resto mantenendo coerenza.
        </p>
        <textarea
            id="characterDescription"
            class="character-description-input"
            placeholder="Esempio: Una ragazza elfica di 24 anni, timida, cresciuta in un villaggio isolato. È brava con la magia ma ha paura dei combattimenti."
        ></textarea>
        <div class="description-footer">
            <span>Vuoto = generazione libera.</span>
            <div class="description-actions">
                <button id="clearCharacterDescription" type="button" class="secondary-button">Pulisci</button>
                <button id="generateFromDescriptionButton" type="button" class="primary-button">✦ Genera da descrizione</button>
            </div>
        </div>
    `;

    identitySection.insertBefore(card, firstCard);

    const input = document.getElementById("characterDescription");

    document.getElementById("clearCharacterDescription")?.addEventListener("click", () => {
        if (input) input.value = "";
        input?.focus();
    });

    document.getElementById("generateFromDescriptionButton")?.addEventListener("click", () => {
        const description = String(input?.value || "").trim();

        if (!description) {
            input?.focus();
            alert("Scrivi prima una breve descrizione del personaggio.");
            return;
        }

        window.dispatchEvent(new CustomEvent("ai-rpg-generate-character", {
            detail: {
                description,
                source: "manual",
                importance: "major"
            }
        }));
    });
}
