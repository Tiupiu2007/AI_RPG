const state = { characters: [] };

const $ = id => document.getElementById(id);

function fullName(c) {
  const i = c.identity || c;
  return [i.name, i.surname].filter(Boolean).join(" ") || `Personaggio #${c.id}`;
}

async function loadCharacters() {
  const response = await fetch('/api/characters');
  if (!response.ok) throw new Error('Impossibile caricare i personaggi.');
  state.characters = await response.json();
  for (const select of [$('fighterA'), $('fighterB')]) {
    for (const c of state.characters) {
      const option = document.createElement('option');
      option.value = c.id;
      option.textContent = fullName(c);
      select.appendChild(option);
    }
  }
  update();
}

function get(id) {
  return state.characters.find(c => Number(c.id) === Number(id));
}

function updatePreview(side) {
  const id = $(side === 'A' ? 'fighterA' : 'fighterB').value;
  const c = get(id);
  const target = $('preview' + side);
  if (!c) { target.textContent = 'Nessun combattente selezionato.'; return; }
  const i = c.identity || c;
  target.innerHTML = `<strong>${fullName(c)}</strong><span>${i.race || 'Razza sconosciuta'} · ${i.age || '?'} anni</span>`;
}

function update() {
  updatePreview('A'); updatePreview('B');
  const a = $('fighterA').value, b = $('fighterB').value;
  $('fightButton').disabled = !a || !b || a === b;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

function render(result) {
  $('title').textContent = result.title || 'Scontro';
  $('introduction').textContent = result.introduction || '';
  $('winner').textContent = result.winner || 'Pareggio';
  $('ending').textContent = result.ending || '';
  $('aftermath').textContent = result.aftermath || '';
  $('rounds').innerHTML = (result.rounds || []).map((r, index) => `
    <article class="round card">
      <div class="round-number">ROUND ${escapeHtml(r.round ?? index + 1)}</div>
      <h3>${escapeHtml(r.title || `Svolta ${index + 1}`)}</h3>
      <p>${escapeHtml(r.narration || '')}</p>
      ${Array.isArray(r.events) ? `<ul>${r.events.map(e => `<li>${escapeHtml(e)}</li>`).join('')}</ul>` : ''}
      <div class="status"><span>${escapeHtml(r.status?.fighter_a || '')}</span><span>${escapeHtml(r.status?.fighter_b || '')}</span></div>
    </article>`).join('');
  $('loading').classList.add('hidden');
  $('result').classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function fight() {
  const a = Number($('fighterA').value), b = Number($('fighterB').value);
  if (!a || !b || a === b) return;
  $('fightButton').disabled = true;
  $('loading').classList.remove('hidden');
  $('result').classList.add('hidden');
  try {
    const response = await fetch('/api/battle', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ character_a_id: a, character_b_id: b, style: $('style').value })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Errore durante lo scontro.');
    render(data);
  } catch (error) {
    $('loading').classList.add('hidden');
    alert(error.message);
  } finally { update(); }
}

$('fighterA').addEventListener('change', update);
$('fighterB').addEventListener('change', update);
$('fightButton').addEventListener('click', fight);
$('againButton').addEventListener('click', () => { $('result').classList.add('hidden'); window.scrollTo({top:0,behavior:'smooth'}); });

loadCharacters().catch(error => alert(error.message));
