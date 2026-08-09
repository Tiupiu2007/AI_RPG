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
            detail: {
                description,
                source: "manual",
                importance: "major"
            }
        }));
    });
}
