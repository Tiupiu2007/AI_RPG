const STAT_NAMES=["strength","constitution","agility","intelligence","perception","willpower","charisma","luck"];
const LABELS={strength:"Forza",constitution:"Costituzione",agility:"Agilità",intelligence:"Intelligenza",perception:"Percezione",willpower:"Volontà",charisma:"Carisma",luck:"Fortuna"};

export function calculateLevel(character){
    const values=STAT_NAMES.map(k=>Number(character?.extra?.statistics?.[k])||0).filter(v=>v>0);
    if(!values.length)return 1;
    const average=values.reduce((a,b)=>a+b,0)/values.length;
    return Math.max(1,Math.min(20,Math.floor((average-30)/3.5)+1));
}

export function updateSummary(character){
    const level=calculateLevel(character);
    const stats=character?.extra?.statistics||{};
    const focus=STAT_NAMES.reduce((best,key)=>(Number(stats[key])||0)>(Number(stats[best])||0)?key:best,"strength");
    const identity=character?.identity||{};
    const name=`${identity.name||"Nuovo"} ${identity.surname||""}`.trim();
    const race=identity.race||"—";
    const age=identity.age||"—";
    const status=character?.extra?.conditions?.status||"Normale";

    const levelElement=document.getElementById("characterLevel");
    const levelText=document.getElementById("characterLevelText");
    const badge=document.getElementById("summaryLevelBadge");
    if(levelElement)levelElement.textContent=level;
    if(levelText)levelText.textContent=level===1?"Personaggio appena creato":`Livello ${level} · ${LABELS[focus]||focus} come caratteristica dominante`;
    if(badge)badge.textContent=`LIV. ${level}`;

    const title=document.getElementById("summaryTitle");
    const text=document.getElementById("summaryText");
    if(title)title.textContent=name||"Nuovo personaggio";
    if(text){
        const personality=character?.personality?.personality_description||"";
        const physical=identity.physical_description||"";
        const base=`${name||"Il personaggio"} è ${race}, ${age} anni.`;
        text.textContent=[base,physical,personality].filter(Boolean).join(" ");
    }
    const set=(id,value)=>{const e=document.getElementById(id);if(e)e.textContent=value;};
    set("summaryRace",race);set("summaryAge",age=== "—"?"—":`${age} anni`);set("summaryFocus",LABELS[focus]||focus);set("summaryStatus",status);
}
