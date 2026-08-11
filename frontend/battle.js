const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
let roomId = params.get('room');
let token = params.get('token');
const state = { characters: [], room: null, busy: false, shareLinks: null, polling: false };

function fullName(c) {
  const i = c.identity || c;
  return [i.name, i.surname].filter(Boolean).join(' ') || `Personaggio #${c.id}`;
}
function esc(v) { return String(v ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[c])); }
function bar(value, max) { const pct = max ? Math.max(0, Math.min(100, value / max * 100)) : 0; return `<div class="bar"><i style="width:${pct}%"></i></div>`; }

async function loadCharacters() {
  const r = await fetch('/api/characters');
  if (!r.ok) throw new Error('Impossibile caricare i personaggi.');
  state.characters = await r.json();
  for (const select of [$('fighterA'), $('fighterB')]) {
    for (const c of state.characters) {
      const o = document.createElement('option'); o.value = c.id; o.textContent = fullName(c); select.appendChild(o);
    }
  }
  updateSetup();
}
function findCharacter(id) { return state.characters.find(c => Number(c.id) === Number(id)); }
function updatePreview(side) {
  const c = findCharacter($(side === 'A' ? 'fighterA' : 'fighterB').value), target = $('preview' + side);
  if (!c) { target.textContent = 'Nessun combattente selezionato.'; return; }
  const i = c.identity || c; target.innerHTML = `<strong>${esc(fullName(c))}</strong><span>${esc(i.race || 'Razza')} · ${esc(i.age || '?')} anni</span>`;
}
function updateSetup() {
  updatePreview('A'); updatePreview('B');
  const a = $('fighterA').value, b = $('fighterB').value;
  $('createRoom').disabled = !a || !b || a === b;
}

function renderShareLinks(data) {
  state.shareLinks = data;
  const links = $('links');
  links.classList.remove('hidden');
  links.innerHTML = `
    <strong>STANZA ${esc(data.room_id)} — LINK DI ACCESSO</strong>
    <label>🎮 ${esc(data.player_a_name || 'Giocatore A')}<input readonly value="${esc(data.player_a_url)}" onclick="this.select()"></label>
    <label>🎮 ${esc(data.player_b_name || 'Giocatore B')}<input readonly value="${esc(data.player_b_url)}" onclick="this.select()"></label>
    <label>👁 ${esc(data.spectator_name || 'Spettatore / Server')}<input readonly value="${esc(data.spectator_url)}" onclick="this.select()"></label>
    <small>Seleziona e copia il link del relativo personaggio. Il link spettatore è quello da conservare tu.</small>`;
}

async function createRoom() {
  const aId = Number($('fighterA').value);
  const bId = Number($('fighterB').value);
  const body = { character_a_id: aId, character_b_id: bId };
  const r = await fetch('/api/pvp/create', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
  const data = await r.json(); if (!r.ok) throw new Error(data.error || 'Errore creazione stanza.');

  data.player_a_name = fullName(findCharacter(aId));
  data.player_b_name = fullName(findCharacter(bId));
  data.spectator_name = 'Spettatore / Server';
  renderShareLinks(data);

  // Il server passa automaticamente alla vista spettatore, ma i link restano visibili.
  roomId = data.room_id;
  token = data.spectator_token;
  history.replaceState({}, '', `/battle.html?room=${data.room_id}&token=${data.spectator_token}`);
  $('setup').classList.add('created');
  await refresh();
  if (!state.polling) { state.polling = true; setInterval(refresh, 900); }
}

function renderFighters(room) {
  const ids = room.turn_order.length ? room.turn_order : Object.keys(room.combatants).map(Number);
  $('fighters').innerHTML = ids.map(id => {
    const c = room.combatants[String(id)];
    const active = room.current_turn_character_id === c.character_id;
    return `<article class="fighter-card ${active ? 'active' : ''} ${c.defeated ? 'defeated' : ''}">
      <div class="fighter-head"><div><span class="fighter-name">${esc(c.name)}</span><span class="fighter-status">${esc(c.status)}</span></div><b>${active ? 'TURNO' : ''}</b></div>
      <div class="resource"><span>HP ${c.health}/${c.max_health}</span>${bar(c.health,c.max_health)}</div>
      <div class="resource"><span>STAMINA ${c.stamina}/${c.max_stamina}</span>${bar(c.stamina,c.max_stamina)}</div>
      <div class="resource"><span>MANA ${c.mana}/${c.max_mana}</span>${bar(c.mana,c.max_mana)}</div>
      <div class="conditions">${(c.conditions || []).map(x => `<span>${esc(x)}</span>`).join('')}</div>
    </article>`;
  }).join('');
}

function renderActions(room) {
  const ownId = room.you_are;
  const own = ownId && ownId !== 'spectator' ? room.combatants[String(ownId)] : null;
  const myTurn = own && room.current_turn_character_id === own.character_id && room.phase === 'active';
  $('roleBadge').textContent = room.is_spectator ? 'SPETTATORE / SERVER' : `GIOCATORE · ${esc(own.name)}`;
  $('actions').classList.toggle('hidden', room.is_spectator);
  if (!own) return;
  $('apLabel').textContent = `PA ${own.action_points}/${own.max_action_points}`;
  const opponent = Object.values(room.combatants).find(c => c.character_id !== own.character_id);
  const buttons = [];
  buttons.push(`<button ${myTurn?'':'disabled'} data-action="attack" class="action physical"><strong>Attacco</strong><small>2 PA · stamina</small></button>`);
  for (const ability of (own.abilities || [])) {
    const name = ability.name || 'Abilità';
    buttons.push(`<button ${myTurn?'':'disabled'} data-action="ability" data-ability="${esc(name)}" class="action magic"><strong>${esc(name)}</strong><small>1 PA · mana</small></button>`);
  }
  buttons.push(`<button ${myTurn?'':'disabled'} data-action="defend" class="action"><strong>Difesa</strong><small>1 PA</small></button>`);
  buttons.push(`<button ${myTurn?'':'disabled'} data-action="recover" class="action"><strong>Recupera</strong><small>1 PA</small></button>`);
  $('actionButtons').innerHTML = buttons.join('');
  $('endTurn').disabled = !myTurn;
  if (opponent) document.querySelectorAll('[data-action]').forEach(btn => btn.onclick = () => sendAction(btn.dataset.action, opponent.character_id, btn.dataset.ability));
  $('endTurn').onclick = () => sendAction('end_turn');
}

function renderLog(room) {
  $('combatLog').innerHTML = room.events.slice().reverse().map(e => `<div class="event ${esc(e.event_type)}"><span>R${esc(e.round_number)}</span><p>${esc(e.description)}</p></div>`).join('');
  $('roundLabel').textContent = `ROUND ${room.round_number}`;
  const active = room.current_turn_character_id ? room.combatants[String(room.current_turn_character_id)] : null;
  $('turnBanner').textContent = room.phase !== 'active' ? (room.winner_id ? `VITTORIA: ${room.combatants[String(room.winner_id)]?.name || '—'}` : 'SCONTRO TERMINATO') : `TURNO DI ${active?.name || '—'}`;
}

async function refresh() {
  if (!roomId || !token) return;
  try {
    const r = await fetch(`/api/pvp/${encodeURIComponent(roomId)}?token=${encodeURIComponent(token)}`);
    const data = await r.json(); if (!r.ok) throw new Error(data.error || 'Stanza non disponibile.');
    state.room = data;
    $('arena').classList.remove('hidden');
    renderFighters(data); renderActions(data); renderLog(data);
    if (!state.shareLinks) $('setup').classList.add('hidden');
  } catch (e) { $('roomLabel').textContent = e.message; }
}

async function sendAction(action, targetId, ability) {
  if (state.busy || !state.room || state.room.is_spectator) return;
  state.busy = true; $('actionMessage').textContent = 'Il server risolve l\'azione...';
  const body = { token, action, target_id: targetId ?? undefined, ability: ability || undefined };
  try {
    const r = await fetch(`/api/pvp/${encodeURIComponent(roomId)}/action`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    const data = await r.json(); if (!r.ok) throw new Error(data.error || 'Azione rifiutata.');
    state.room = data; renderFighters(data); renderActions(data); renderLog(data); $('actionMessage').textContent = '';
  } catch (e) { $('actionMessage').textContent = e.message; }
  finally { state.busy = false; }
}

$('fighterA').addEventListener('change', updateSetup);
$('fighterB').addEventListener('change', updateSetup);
$('createRoom').addEventListener('click', () => createRoom().catch(e => alert(e.message)));

(async () => {
  if (roomId && token) { await refresh(); if (!state.polling) { state.polling = true; setInterval(refresh, 900); } return; }
  try { await loadCharacters(); } catch (e) { alert(e.message); }
})();
