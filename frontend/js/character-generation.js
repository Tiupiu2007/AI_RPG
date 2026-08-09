import { normalizeCharacter, saveLocalCharacter } from "./character-state.js";
import { generateCharacterFromAPI, saveCharacterToAPI } from "./character-api.js";
import { resetGeneration, setProgress, setGenerationStep, wait, activateSection } from "./character-ui.js";

export async function generateCharacter(onGenerated, options = {}) {
    const generateButton = document.getElementById("generateButton");
    const newButton = document.getElementById("newCharacterButton");
    const overlay = document.getElementById("generationOverlay");
    const generationName = document.getElementById("generationName");
    const descriptionInput = document.getElementById("characterDescription");

    if (!generateButton || generateButton.disabled) return null;

    const description = String(options.description ?? descriptionInput?.value ?? "").trim();
    const source = options.source || (description ? "manual" : "system");
    const importance = options.importance || "major";

    generateButton.disabled = true;
    if (newButton) newButton.disabled = true;
    overlay?.classList.remove("hidden");
    resetGeneration();

    try {
        setGenerationStep("stepRace", "active");
        setProgress(10, description ? "Analisi della descrizione e scelta della razza..." : "Scelta della razza e generazione del personaggio...");
        const generated = await generateCharacterFromAPI(description, source, importance);
        setGenerationStep("stepRace", "completed");
        setGenerationStep("stepIdentity", "active");
        setProgress(30, "Identità, corpo e aspetto generati...");
        await wait(120);
        setGenerationStep("stepIdentity", "completed");
        setGenerationStep("stepLanguages", "active");
        setProgress(45, "Lingue assegnate in base alla razza...");
        await wait(120);
        setGenerationStep("stepLanguages", "completed");
        setGenerationStep("stepAppearance", "active");
        setProgress(60, "Statistiche personali e stato iniziale...");
        await wait(120);
        setGenerationStep("stepAppearance", "completed");
        setGenerationStep("stepConsistency", "active");
        setProgress(78, "Psicologia, personalità, abilità e skill...");

        const character = normalizeCharacter(generated);

        // Salva subito il nuovo personaggio nello storage prima di aggiornare
        // i moduli secondari. In questo modo il riepilogo/profilo legge già
        // il personaggio appena generato e non quello precedente.
        saveLocalCharacter(character);
        onGenerated(character);
        window.dispatchEvent(new CustomEvent("ai-rpg-character-changed", {
            detail: character
        }));

        await wait(150);
        setGenerationStep("stepConsistency", "completed");
        setGenerationStep("stepComplete", "active");
        setProgress(92, "Salvataggio completo nel database...");

        const saved = await saveCharacterToAPI(character);
        if (saved?.id) character.id = saved.id;
        saveLocalCharacter(character);

        window.dispatchEvent(new CustomEvent("ai-rpg-character-changed", {
            detail: character
        }));

        setGenerationStep("stepComplete", "completed");
        setProgress(100, "Personaggio completato e salvato.");
        if (generationName) generationName.textContent = `${character.identity.name} ${character.identity.surname}`.trim();

        await wait(700);
        overlay?.classList.add("hidden");
        activateSection("identity");
        return character;
    } catch (error) {
        console.error("Errore durante la generazione:", error);
        if (generationName) generationName.textContent = "Generazione fallita";
        setProgress(100, error.message);
        alert(`Non è stato possibile generare il personaggio.\n\n${error.message}`);
        await wait(700);
        overlay?.classList.add("hidden");
        throw error;
    } finally {
        generateButton.disabled = false;
        if (newButton) newButton.disabled = false;
    }
}
