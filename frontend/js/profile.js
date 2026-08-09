export const PROFILE_FIELDS=["mentalState","emotionalStability","fears","desires","values","traumas","personalityDescription","traits","strengths","flaws","habits","socialBehavior"];
const PSY={mentalState:"mental_state",emotionalStability:"emotional_stability",fears:"fears",desires:"desires",values:"values",traumas:"traumas"};
const PER={personalityDescription:"personality_description",traits:"traits",strengths:"strengths",flaws:"flaws",habits:"habits",socialBehavior:"social_behavior"};
export function loadProfileIntoUI(character){PROFILE_FIELDS.forEach(f=>{const i=document.getElementById(f);if(!i)return;const k=PSY[f]||PER[f];const s=PSY[f]?character.psychology:character.personality;i.value=s?.[k]||"";});}
export function updateProfileFromUI(character){PROFILE_FIELDS.forEach(f=>{const i=document.getElementById(f);if(!i)return;if(PSY[f])character.psychology[PSY[f]]=i.value.trim();if(PER[f])character.personality[PER[f]]=i.value.trim();});}
export function bindProfileInputs(callback){PROFILE_FIELDS.forEach(f=>document.getElementById(f)?.addEventListener("input",callback));}
