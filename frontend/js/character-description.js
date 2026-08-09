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
        <p class="description-hint">Scrivi poche informazioni sul personaggio. Il sistema completerà automaticamente tutto ciò che manca.</p>
        <textarea id="characterDescription" class="character-description-input" placeholder="Esempio: Una ragazza elfica di 24 anni, timida, cresciuta in un villaggio isolato. È brava con la magia ma ha paura dei combattimenti."></textarea>
        <div class="description-footer">
            <span>Lascia vuoto per una generazione completamente casuale.</span>
            <button id="clearCharacterDescription" type="button" class="secondary-button">Pulisci</button>
        </div>
    `;

    identitySection.insertBefore(card, firstCard);

    document.getElementById("clearCharacterDescription")?.addEventListener("click", () => {
        const input = document.getElementById("characterDescription");
        if (input) input.value = "";
    });
}
