# AI RPG — Stato del progetto

## Core completato

- [x] Chat narrativa libera senza menu.
- [x] Player agency separata dal narratore.
- [x] Pipeline intent AI → Game Engine → Narration AI.
- [x] Stato autorevole di HP, stamina, mana, inventario, posizione e flag.
- [x] Validazione delle azioni AI.
- [x] Memoria persistente con recupero per rilevanza.
- [x] Fatti canonici persistenti.
- [x] Eventi persistenti.
- [x] Relazioni persistenti.
- [x] Interazioni NPC con memoria e conoscenza separate.
- [x] Mondo persistente con orologio e cronologia eventi.
- [x] Luoghi persistenti e scoperta di nuove destinazioni esplicitamente indicate dal PLAYER.
- [x] Movimento collegato al Game Engine.
- [x] Combattimento narrativo persistente.
- [x] Danni, costi, risorse e condizioni calcolati dal combat engine.
- [x] Persistenza delle conseguenze del combattimento sui personaggi.
- [x] Reset della storia con stato narrativo e mondo separati.
- [x] API per stato del personaggio e stato del mondo.
- [x] Test dei contratti principali del Game Engine.

## Da completare solo se si vogliono sistemi RPG più profondi

Questi elementi non sono necessari per il nucleo conversazionale persistente, ma possono essere aggiunti in seguito senza cambiare l'architettura:

- [ ] Sistema quest strutturato con obiettivi, ricompense e stati.
- [ ] Economia e commercio realmente collegati alle azioni narrative.
- [ ] Equipaggiamento con statistiche, usura e riparazione.
- [ ] Progressione esperienza/livello.
- [ ] Sistema di reputazione/fazioni collegato agli eventi.
- [ ] Simulazione autonoma avanzata degli NPC fuori scena.
- [ ] Mappa grafica.
- [ ] UI avanzata per inventario, statistiche, relazioni e mondo.
- [ ] Packaging standalone/Steam con provider AI integrato.
- [ ] Test end-to-end con un'istanza reale di Ollama.

## Regola architetturale

L'AI interpreta e racconta. Il Game Engine decide cosa è realmente successo. La memoria e il World State conservano ciò che deve continuare a essere vero.

Il mondo può essere creativo. Il personaggio del PLAYER non viene inventato dall'AI.
