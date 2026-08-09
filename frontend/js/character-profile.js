const PROFILE_STORAGE_KEY = "ai-rpg-character-profile";

const profileFields = [
    "mentalState", "emotionalStability", "fears", "desires", "values", "traumas",
    "personalityDescription", "traits", "strengths", "flaws", "habits", "socialBehavior"
];

function getEmptyProfile() {
    return Object.fromEntries(profileFields.map(field => [field, ""]));
}

function loadProfile() {
    let saved = {};
    try {
        saved = JSON.parse(localStorage.getItem(PROFILE_STORAGE_KEY) || "{}");
    } catch (error) {
        console.warn("Profilo psicologico non valido.", error);
    }

    const profile = {
        ...getEmptyProfile(),
        ...(saved && typeof saved === "object" ? saved : {})
    };

    profileFields.forEach(field => {
        const input = document.getElementById(field);
        if (input) input.value = profile[field] || "";
    });
}

function saveProfile() {
    const profile = {};
    profileFields.forEach(field => {
        const input = document.getElementById(field);
        profile[field] = input ? input.value.trim() : "";
    });
    localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
}

function initializeProfileEditor() {
    loadProfile();
    profileFields.forEach(field => {
        const input = document.getElementById(field);
        if (input) input.addEventListener("input", saveProfile);
    });
}

document.addEventListener("DOMContentLoaded", initializeProfileEditor);
