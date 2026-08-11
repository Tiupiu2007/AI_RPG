const $=id=>document.getElementById(id);
const STAT_NAMES=['strength','constitution','agility','intelligence','perception','willpower','charisma','luck'];
const EFFECT_TYPES={damage:'Danno',heal:'Cura',gain_stamina:'Recupera stamina',gain_mana:'Recupera mana',apply_condition:'Applica condizione',remove_condition:'Rimuovi condizione',draw_cards:'Pesca carte',discard_random:'Scarta carte'};
let catalog=[],currentCard=null;

async function api(url,options={}){
 const r=await fetch(url,options);
 const data=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(data.error||`Errore HTTP ${r.status}`);
 return data;
}
async function loadCatalog(){try{catalog=await api('/api/cards');renderCatalog();if(catalog[0])loadCard(catalog[0]);else resetForm();}catch(e){document.body.innerHTML=`<main style="max-width:700px;margin:80px auto;padding:30px;background:#11141b;color:#edf0f5;border:1px solid #303746;border-radius:16px;font-family:Segoe UI,Arial"><h1>Laboratorio carte</h1><p>${esc(e.message)}</p><p>Questa sezione è riservata al server/amministratore.</p></main>`;}}
function value(id){return $(id).value.trim();}
function list(id){return value(id).split(',').map(x=>x.trim()).filter(Boolean);}
function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[c]));}
function effectDefaults(type='damage'){
 const base={type};
 if(type==='damage')Object.assign(base,{amount:10,damage_type:'physical'});
 if(type==='heal'||type==='gain_stamina'||type==='gain_mana'||type==='draw_cards'||type==='discard_random')base.amount=5;
 if(type==='apply_condition')Object.assign(base,{condition:'bruciatura',amount:1,duration_turns:2});
 if(type==='remove_condition')base.condition='stordito';
 return base;
}
function createEffectRow(effect=effectDefaults(),index){
 const row=document.createElement('div');row.className='effect-row';row.dataset.index=index;
 row.innerHTML=`<div class="effect-head"><strong>Effetto ${index+1}</strong><button type="button" class="remove-effect">Rimuovi</button></div><div class="grid2"><label>Tipo<select class="effect-type">${Object.entries(EFFECT_TYPES).map(([k,v])=>`<option value="${k}" ${effect.type===k?'selected':''}>${v}</option>`).join('')}</select></label><label>Quantità<input class="effect-amount" type="number" min="0" value="${effect.amount??0}"></label></div><div class="effect-fields"></div>`;
 $('effectsList').appendChild(row);
 row.querySelector('.effect-type').addEventListener('change',()=>{renderEffectFields(row,effectDefaults(row.querySelector('.effect-type').value));refreshPreview();});
 row.querySelector('.effect-amount').addEventListener('input',refreshPreview);
 row.querySelector('.remove-effect').onclick=()=>{row.remove();renumberEffects();refreshPreview();};
 renderEffectFields(row,effect);return row;
}
function renderEffectFields(row,effect){
 const type=row.querySelector('.effect-type').value,box=row.querySelector('.effect-fields');let html='';
 if(type==='damage')html=`<div class="grid2"><label>Tipo danno<input class="effect-damage-type" value="${esc(effect.damage_type||'physical')}"></label><label>Critico? <select class="effect-critical"><option value="false">No</option><option value="true" ${effect.critical?'selected':''}>Sì</option></select></div>`;
 if(type==='apply_condition')html=`<div class="grid2"><label>Condizione<input class="effect-condition" value="${esc(effect.condition||'bruciatura')}"></label><label>Durata turni<input class="effect-duration" type="number" min="1" value="${effect.duration_turns??2}"></label></div>`;
 if(type==='remove_condition')html=`<label>Condizione da rimuovere<input class="effect-condition" value="${esc(effect.condition||'stordito')}"></label>`;
 if(type==='draw_cards'||type==='discard_random')html=`<small>La quantità indica quante carte vengono pescate/scartate.</small>`;
 box.innerHTML=html;box.querySelectorAll('input,select').forEach(el=>el.addEventListener('input',refreshPreview));
}
function renumberEffects(){document.querySelectorAll('.effect-row').forEach((r,i)=>r.querySelector('.effect-head strong').textContent=`Effetto ${i+1}`);}
function readEffects(){return [...document.querySelectorAll('.effect-row')].map(row=>{const type=row.querySelector('.effect-type').value;const out={type};const amount=row.querySelector('.effect-amount');if(amount)out.amount=Number(amount.value||0);const damage=row.querySelector('.effect-damage-type');if(damage)out.damage_type=damage.value.trim()||'physical';const critical=row.querySelector('.effect-critical');if(critical)out.critical=critical.value==='true';const condition=row.querySelector('.effect-condition');if(condition)out.condition=condition.value.trim();const duration=row.querySelector('.effect-duration');if(duration)out.duration_turns=Math.max(1,Number(duration.value||1));return out;});}
function setEffects(effects){$('effectsList').innerHTML='';(Array.isArray(effects)&&effects.length?effects:[effectDefaults()]).forEach((e,i)=>createEffectRow(e,i));}
function buildCard(){const statistics={};document.querySelectorAll('[data-stat]').forEach(i=>{const n=Number(i.value);if(n>0)statistics[i.dataset.stat]=n;});const resource=value('resource');const cost=Number($('cost').value||0);return{id:value('id'),name:value('name'),type:value('type'),rarity:value('rarity'),cost,resource,action_points_cost:Number($('actionPointsCost').value||0),mana_cost:resource==='mana'?cost:0,target:value('target'),description:value('description'),flavor:value('flavor'),image:value('image'),requirements:{statistics,races:list('races'),tags:list('requiredTags'),requires_cards:list('requiresCards'),min_level:Number($('minLevel').value||1)},effects:readEffects(),tags:list('cardTags')};}
function renderPreview(card){const image=card.image?`<img src="${esc(card.image)}" onerror="this.parentElement.innerHTML='<span>Immagine non trovata</span>'">`:'<span>IMMAGINE</span>';const effects=(card.effects||[]).map(e=>`<span>${esc(EFFECT_TYPES[e.type]||e.type)}${e.amount!=null?` · ${e.amount}`:''}${e.condition?` · ${esc(e.condition)}`:''}</span>`).join('');$('cardPreview').innerHTML=`<div class="art">${image}</div><div class="meta"><span>${esc(card.type)} · ${esc(card.rarity)} · ${esc(card.target||'enemy')}</span><span class="cost-badge">${esc(card.resource==='mana'?`${card.cost} MANA + ${card.action_points_cost||1} PA`:`${card.action_points_cost||card.cost} PA`)}</span></div><h2>${esc(card.name||'Nome carta')}</h2><p>${esc(card.description||'Descrizione della carta.')}</p><p><em>${esc(card.flavor||'')}</em></p><div class="tags">${Object.entries(card.requirements?.statistics||{}).map(([k,v])=>`<span>${esc(k)} ≥ ${v}</span>`).join('')}${(card.requirements?.races||[]).map(x=>`<span>${esc(x)}</span>`).join('')}${(card.requirements?.requires_cards||[]).map(x=>`<span>↳ ${esc(x)}</span>`).join('')}${effects}</div>`;$('jsonOutput').textContent=JSON.stringify(card,null,2);}
function refreshPreview(){const c=buildCard();currentCard=c;renderPreview(c);}
function loadCard(card){currentCard=JSON.parse(JSON.stringify(card));$('id').value=card.id||'';$('name').value=card.name||'';$('type').value=card.type||'skill';$('rarity').value=card.rarity||'common';$('cost').value=card.cost??1;$('resource').value=card.resource||'action_points';$('actionPointsCost').value=card.action_points_cost??1;$('target').value=card.target||'enemy';$('description').value=card.description||'';$('flavor').value=card.flavor||'';$('image').value=card.image||'';$('minLevel').value=card.requirements?.min_level??1;$('races').value=(card.requirements?.races||[]).join(', ');$('requiresCards').value=(card.requirements?.requires_cards||[]).join(', ');$('requiredTags').value=(card.requirements?.tags||[]).join(', ');$('cardTags').value=(card.tags||[]).join(', ');document.querySelectorAll('[data-stat]').forEach(i=>i.value=card.requirements?.statistics?.[i.dataset.stat]??'');setEffects(card.effects);refreshPreview();}
function resetForm(){currentCard=null;$('cardForm').reset();document.querySelectorAll('[data-stat]').forEach(x=>x.value='');$('cost').value=1;$('actionPointsCost').value=1;$('minLevel').value=1;$('target').value='enemy';$('effectsList').innerHTML='';createEffectRow(effectDefaults(),0);refreshPreview();}
function renderCatalog(){ $('catalog').innerHTML=catalog.map((c,i)=>`<div class="catalog-item"><div class="thumb">${c.image?`<img src="${esc(c.image)}">`:''}</div><div><strong>${esc(c.name)}</strong><small>${esc(c.id)} · ${esc(c.rarity)} · ${c.cost} ${esc(c.resource)}</small></div><button type="button" data-load="${i}">Apri</button></div>`).join('');document.querySelectorAll('[data-load]').forEach(b=>b.onclick=()=>loadCard(catalog[Number(b.dataset.load)]));}
$('stats').innerHTML=STAT_NAMES.map(s=>`<label>${s}<input data-stat="${s}" type="number" min="0" placeholder="nessun requisito"></label>`).join('');
$('addEffect').onclick=()=>{createEffectRow(effectDefaults(),document.querySelectorAll('.effect-row').length);refreshPreview();};
$('resetBtn').onclick=resetForm;
$('cardForm').addEventListener('submit',async e=>{e.preventDefault();const card=buildCard();if(!card.id||!card.name)return alert('Inserisci ID e nome.');try{const data=await api('/api/cards',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(card)});catalog=await api('/api/cards');currentCard=data.card;renderCatalog();loadCard(data.card);alert('Carta salvata dal server.');}catch(error){alert(error.message);}});
$('cardForm').addEventListener('input',refreshPreview);
$('copyBtn').onclick=async()=>{await navigator.clipboard.writeText($('jsonOutput').textContent);$('copyBtn').textContent='Copiato ✓';setTimeout(()=>$('copyBtn').textContent='Copia JSON',1200);};
$('downloadBtn').onclick=()=>{const blob=new Blob([JSON.stringify(buildCard(),null,2)+'\n'],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${buildCard().id||'carta'}.json`;a.click();URL.revokeObjectURL(a.href);};
loadCatalog();