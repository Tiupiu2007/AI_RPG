// =========================================================
// AI RPG - CHARACTER API
// =========================================================

export async function loadWorldData() {
    const racesResponse = await fetch("/api/races");
    if (!racesResponse.ok) throw new Error("Impossibile caricare le razze.");
    const races = await racesResponse.json();

    const languagesResponse = await fetch("/api/languages");
    if (!languagesResponse.ok) throw new Error("Impossibile caricare le lingue.");
    const languages = await languagesResponse.json();

    return { races, languages };
}

export async function getRaceLanguages(race) {
    const response = await fetch("/api/race-languages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race })
    });
    const data = await response.json().catch(() => []);
    if (!response.ok) throw new Error(data.error || "Impossibile caricare le lingue della razza.");
    return data;
}

export async function generateCharacterFromAPI(description = "", source = "system", importance = "major") {
    const response = await fetch("/api/generate-character", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description, source, importance })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Generazione fallita.");
    return data;
}

export async function saveCharacterToAPI(character) {
    const response = await fetch("/api/characters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(character)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Salvataggio sul database fallito.");
    return data;
}
