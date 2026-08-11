const $ = id => document.getElementById(id);
const STAT_NAMES = ['strength','constitution','agility','intelligence','perception','willpower','charisma','luck'];
let catalog = [];
let currentCard = null;

async function loadCatalog(){
  try{const r=await fetch('/cards-data.json');catalog=await r.json();}catch{catalog=[];}
  renderCatalog();
  if(catalog[0]) loadCard(catalog[0]); else updatePreview(buildCard());
}

function value(id){return $(id).value.trim();}
function list(id){return value(id).split(',').map(x=>x.trim()).filter(Boolean);}

function buildCard(){
  const statistics={};
  document.querySelectorAll('[data-stat]').forEach(input=>{const n=Number(input.value);if(n>0)statistics[input.dataset.stat]=n;});
  return {
    id:value('id'),name:value('name'),type:value('type'),rarity:value('rarity'),cost:Number($('cost').value||0),resource:value('resource'),
    description:value('description'),flavor:value('flavor'),image:value('image'),
    requirements:{statistics,races:list('races'),tags:list('requiredTags'),requires_cards:list('requiresCards'),min_level:Number($('minLevel').value||1)},
    effects: currentCard?.effects || [{type:'damage',amount:10,damage_type:'physical'}],
    tags:[]
  };
}

function renderPreview(card){
  const image=card.image ? `<img src="${esc(card.image)}" onerror="this.parentElement.innerHTML='Immagine non trovata';">` : 'IMMAGINE';
  $('cardPreview').innerHTML=`<div class="art">${image}</div><div class="meta"><span>${esc(card.type)} · ${esc(card.rarity)}</span><span class="cost-badge">${esc(card.cost)} ${esc(card.resource)}</span></div><h2>${esc(card.name||'Nome carta')}</h2><p>${esc(card.description||'Descrizione della carta.')}</p><p><em>${esc(card.flavor||'')}</em></p><div class="tags">${Object.entries(card.requirements.statistics||{}).map(([k,v])=>`<span>${esc(k)} ≥ ${v}</span>`).join('')}${(card.requirements.races||[]).map(x=>`<span>${esc(x)}</span>`).join('')}${(card.requirements.requires_cards||[]).map(x=>`<span>↳ ${esc(x)}</span>`).join('')}</div>`;
  $('jsonOutput').textContent=JSON.stringify(card,null,2);
}
function updatePreview(card){currentCard=card;renderPreview(card);}
function loadCard(card){
  currentCard=JSON.parse(JSON.stringify(card));
  $('id').value=card.id||'';$('name').value=card.name||'';$('type').value=card.type||'skill';$('rarity').value=card.rarity||'common';$('cost').value=card.cost??1;$('resource').value=card.resource||'action_points';$('description').value=card.description||'';$('flavor').value=card.flavor||'';$('image').value=card.image||'';$('minLevel').value=card.requirements?.min_level??1;$('races').value=(card.requirements?.races||[]).join(', ');$('requiresCards').value=(card.requirements?.requires_cards||[]).join(', ');$('requiredTags').value=(card.requirements?.tags||[]).join(', ');
  document.querySelectorAll('[data-stat]').forEach(input=>input.value=card.requirements?.statistics?.[input.dataset.stat]??'');
  updatePreview(card);
}
function renderCatalog(){
  $('catalog').innerHTML=catalog.map((card,i)=>`<div class="catalog-item"><div class="thumb">${card.image?`<img src="${esc(card.image)}">`:''}</div><div><strong>${esc(card.name)}</strong><small>${esc(card.id)} · ${esc(card.rarity)} · ${card.cost} ${esc(card.resource)}</small></div><button type="button" data-load="${i}">Apri</button></div>`).join('');
  document.querySelectorAll('[data-load]').forEach(b=>b.onclick=()=>loadCard(catalog[Number(b.dataset.load)]));
}
function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[c]));}

$('cardForm').addEventListener('submit',e=>{e.preventDefault();const card=buildCard();if(!card.id||!card.name)return alert('Inserisci ID e nome.');catalog=[...catalog.filter(x=>x.id!==card.id),card];currentCard=card;renderCatalog();renderPreview(card);});
$('resetBtn').onclick=()=>{currentCard=null;$('cardForm').reset();document.querySelectorAll('[data-stat]').forEach(x=>x.value='');$('cost').value=1;$('minLevel').value=1;updatePreview(buildCard());};
$('copyBtn').onclick=async()=>{await navigator.clipboard.writeText($('jsonOutput').textContent);$('copyBtn').textContent='Copiato ✓';setTimeout(()=>$('copyBtn').textContent='Copia JSON',1200);};
$('cardForm').addEventListener('input',()=>updatePreview(buildCard()));

const statBox= $('stats');statBox.innerHTML=STAT_NAMES.map(s=>`<label>${s}<input data-stat="${s}" type="number" min="0" placeholder="nessun requisito"></label>`).join('');
loadCatalog();
