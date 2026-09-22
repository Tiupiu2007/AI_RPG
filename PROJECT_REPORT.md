# AI_RPG — Report del progetto

Ultimo aggiornamento: 22 settembre 2026

## 1. Scopo

AI_RPG è un RPG narrativo persistente in italiano. Il giocatore scrive liberamente cosa vuole fare e l'IA agisce come Game Master.

Principio fondamentale:

> Il mondo appartiene al narratore. Il personaggio appartiene al giocatore.

L'obiettivo tecnico è separare progressivamente la libertà narrativa dell'IA dalla gestione autorevole dello stato di gioco.

---

## 2. Stack attuale

- Python 3.14.2
- Ollama 0.32.6
- Modello previsto: qwen3:30b-a3b-instruct-2507-q4_K_M
- Backend Python
- Frontend HTML/CSS/JavaScript
- Database SQLite: `data/game.db`
- API locali tramite `server.py`
- Git branch principale: `main`

---

## 3. Avvio

Il progetto può essere avviato con:

1. Ollama in esecuzione.
2. Modello Ollama disponibile.
3. `python server.py`
4. Apertura di `http://127.0.0.1:8000/chat.html`

È presente anche `avvia_ai_rpg.bat` per facilitare l'avvio su Windows.

---

## 4. Sistema narrativo — FUNZIONANTE

Il file principale è:

`app/story_chat.py`

Il sistema attuale:

- riceve un messaggio libero del giocatore;
- mantiene la cronologia della storia;
- usa fino a 40 messaggi di cronologia;
- passa gli ultimi 12 messaggi al prompt;
- recupera memorie persistenti pertinenti al messaggio corrente;
- recupera eventi recenti;
- passa al narratore le relazioni persistenti del personaggio;
- indicizza i fatti canonici importanti anche nel sistema di memoria;
- passa all'IA lo stato autorevole del Game Engine;
- salva la risposta dell'IA;
- registra ogni turno come evento;
- supporta memorie esplicite tramite frasi come "ricordati...";
- mantiene un canone persistente del mondo tramite `world_canon`;
- limita il canone a 100 fatti;
- richiede all'IA un JSON con narrazione e nuovi fatti canonici.

---

## 5. Regole narrative attualmente implementate

L'IA è istruita a:

- parlare del giocatore sempre in seconda persona;
- non controllare il personaggio del giocatore;
- non inventare azioni, dialoghi, pensieri, emozioni o decisioni del giocatore;
- non inventare equipaggiamento, magie, abilità, ferite, ricordi o relazioni personali non presenti nel contesto;
- considerare il Game Engine come fonte autorevole per i dati meccanici;
- mantenere la continuità tra i turni;
- non contraddire fatti già stabiliti;
- distinguere ciò che il personaggio sa da ciò che conosce il narratore;
- permettere al narratore di costruire liberamente l'ambiente;
- usare la scoperta progressiva dei dettagli;
- non rivelare automaticamente tutto ciò che esiste in una scena;
- non trasformare ogni osservazione in un mistero;
- evitare rune, scritte criptiche, maledizioni e soprannaturale senza una ragione narrativa;
- descrivere normalmente materiali, forme, luce, sporco, usura e oggetti;
- non aggiungere necessariamente un dettaglio importante a ogni turno;
- lasciare al giocatore la scelta delle azioni successive;
- determinare le conseguenze plausibili delle azioni rischiose senza garantire automaticamente il successo;
- evitare menu A/B/C e risposte a scelta multipla;
- mantenere un ritmo normalmente breve, di circa 30-120 parole.

---

## 6. Canone persistente — FUNZIONANTE

I fatti importanti stabiliti durante la narrazione possono essere restituiti dall'IA in:

`canon_facts`

Questi vengono salvati in:

`extra["world_canon"]`

Il sistema evita di trasformare ogni frase narrativa in un fatto persistente.

Il canone viene eliminato quando si resetta completamente la storia del personaggio.

---

## 7. Game Engine — PRESENTE E COLLEGATO

Il Game Engine si trova in:

`app/game_engine/__init__.py`

Gestisce una base di stato autorevole contenente:

- posizione;
- flag;
- effetti attivi;
- turno;
- HP;
- HP massimi;
- stamina;
- stamina massima;
- mana;
- mana massima;
- stato/condizione;
- inventario;
- statistiche;
- abilità;
- skill;
- magia.

Sono presenti funzioni per:

- inizializzare lo stato;
- creare snapshot dello stato;
- avanzare il turno;
- spendere risorse;
- ripristinare risorse;
- modificare la salute;
- impostare flag;
- controllare flag;
- cambiare posizione;
- aggiungere oggetti;
- rimuovere oggetti.

Lo stato è esposto anche tramite:

`/api/game-state/<character_id>`

### Flusso attuale

L'azione strutturata prodotta dall'IA passa ora da `execute_action()` prima di diventare stato reale. Le azioni non valide non vengono applicate e non vengono narrate come riuscite.

L'architettura è:

```
PLAYER
↓
interpretazione dell'intento
↓
validazione/calcolo del GAME ENGINE
↓
modifica reale dello stato
↓
narrazione dell'esito
```

Questa è una delle prossime fasi principali.

---

## 8. Database e personaggi

Il progetto dispone di un sistema di personaggi con:

- identità;
- lingue;
- profilo;
- razze;
- inventario;
- magia;
- denaro;
- statistiche;
- abilità;
- stato;
- dati extra persistenti.

La gestione principale passa da:

`app/database/characters_db.py`

Il sistema narrativo utilizza il personaggio presente nel database come fonte del contesto.

---

## 9. Memoria ed eventi — PRESENTI

Directory:

`app/memory/`

Sono presenti:

- gestione della memoria;
- contesto;
- eventi recenti;
- memoria persistente;
- reset della cronologia.

Il normale testo della narrazione non viene automaticamente trasformato in memoria persistente.

Una richiesta esplicita come:

`ricordati che ...`

viene salvata separatamente.

---

## 10. Mondo di gioco — PRESENTE

Directory:

`app/world/`

Sono presenti sistemi/moduli per:

- biomi;
- consumo;
- demografia;
- economia;
- ambiente;
- fazioni;
- geografia;
- logistica;
- luoghi;
- movimento;
- pathfinding;
- popolazione;
- posizioni;
- regioni;
- sicurezza;
- condizioni degli insediamenti;
- insediamenti;
- tempo;
- commercio;
- repository del mondo;
- stato del mondo.

Questi moduli costituiscono la base per un mondo simulato persistente.

---

## 11. Combattimento — PRESENTE, NON ANCORA PARTE DEL FLUSSO NARRATIVO PRINCIPALE

Sono presenti sistemi separati per:

- modelli di combattimento;
- simulazione del combattimento;
- AI di battaglia;
- deck;
- simulatore di combattimento;
- validazione/esecuzione di alcune azioni.

Il frontend contiene anche una pagina dedicata al simulatore di combattimento.

Questo sistema esiste nel repository, ma il collegamento completo tra:

`azione libera del giocatore → Game Engine → combattimento → narrazione`

è ancora da completare.

---

## 12. Relazioni e interazioni

Sono presenti moduli per:

- relazioni;
- interazione tra personaggi;
- gestione delle relazioni persistenti.

La narrazione può utilizzare i dati disponibili, ma il sistema completo di NPC persistenti e relazioni dinamiche deve ancora essere integrato nel flusso principale.

---

## 13. Frontend — PRESENTE

Il frontend contiene interfacce per:

- pagina principale;
- chat narrativa;
- gestione personaggi;
- descrizione personaggio;
- profilo;
- sezioni del personaggio;
- riepilogo;
- stato;
- inventario;
- database;
- lingue;
- combattimento;
- simulatore di combattimento.

Sono presenti file HTML, CSS e JavaScript separati.

---

## 14. API / Backend

`server.py` gestisce il server locale e le API del progetto.

Tra le funzioni già collegate al sistema narrativo c'è l'accesso allo stato autorevole del Game Engine.

Il backend collega:

- database;
- personaggi;
- memoria;
- eventi;
- Game Engine;
- provider AI;
- frontend.

---

## 15. Provider AI

Il progetto dispone di:

`app/ai_provider.py`

e del relativo package:

`app/ai_provider/`

Il sistema è predisposto per comunicare con Ollama e utilizzare il modello locale.

La configurazione narrativa attuale richiede risposte strutturate JSON per evitare che la risposta dell'IA venga interpretata liberamente dal backend.

---

## 16. Test

Sono presenti test per varie parti del progetto, inclusi:

- database personaggi;
- identità;
- movimento del mondo;
- popolazione degli insediamenti.

Il progetto contiene inoltre script di supporto per il reset dei dati di test.

La presenza dei test non significa che ogni sistema dell'intero progetto sia coperto o completamente verificato.

---

## 17. Documentazione

La documentazione tecnica utile rimane nella directory:

`docs/`

Sono presenti specifiche per:

- personaggi;
- inventario;
- magia;
- mondo;
- TODO.

Sono presenti inoltre:

- `README.md`
- `AI_MODEL.md`

Questo file costituisce il report generale dello stato del progetto; le specifiche tecniche dettagliate restano nei rispettivi documenti.

---

## 18. Cosa funziona oggi nel nucleo RPG

### Architettura narrativa persistente

Il turno principale usa una pipeline a tre fasi:

1. Intent AI — interpreta il messaggio del PLAYER senza decidere il risultato.
2. Game Engine — valida ed esegue l'azione e applica le modifiche reali.
3. Narration AI — riceve lo stato già aggiornato e racconta esclusivamente il risultato.

Il mondo possiede un proprio salvataggio SQLite (data/worlds.db) con orologio, eventi e stato persistente. Il personaggio mantiene il collegamento al proprio world_id.

La memoria usa recupero per rilevanza, oltre alla memoria recente. I fatti canonici importanti vengono indicizzati come memorie persistenti.

Le interazioni NPC hanno memoria propria, relazioni persistenti, conoscenza separata dal PLAYER e azioni validate dal game engine.

Il combattimento narrativo è persistente: uno scontro può continuare attraverso più messaggi, il motore calcola danni, costi ed esiti e le condizioni risultanti vengono riportate nei personaggi.


### FUNZIONANTE

- chat narrativa locale;
- comunicazione con Ollama;
- cronologia della storia;
- memoria persistente;
- eventi;
- reset della storia;
- canone persistente;
- contesto del personaggio;
- seconda persona;
- protezione dell'agency del giocatore tramite prompt;
- protezione dei dati personali del personaggio tramite prompt;
- Game Engine collegato al sistema narrativo;
- stato autorevole esposto al backend/frontend;
- stato base di HP/stamina/mana/inventario/posizione/flag;
- frontend della chat;
- database dei personaggi.

### INTEGRAZIONE ANCORA NECESSARIA

- regole complete per attacco/difesa/magia con costi e conseguenze meccaniche;
- combattimento narrativo integrato end-to-end;
- sistema NPC completo con memoria individuale, conoscenze e obiettivi aggiornati dal mondo;
- aggiornamento automatico delle relazioni in base agli eventi sociali;
- quest persistenti e obiettivi di lungo periodo;
- simulazione completa del mondo collegata al passaggio del tempo;
- save/load completo e versionato dell'intero mondo;
- packaging/distribuzione con provider AI installabile senza Ollama manuale.

---

## 19. Prossime priorità

L'ordine consigliato per continuare il progetto è:

1. Completare le regole meccaniche di tutte le azioni.
2. Integrare combattimento, NPC e relazioni nel turno narrativo.
3. Implementare quest e obiettivi persistenti.
4. Collegare il simulatore del mondo al tempo di gioco.
5. Implementare save/load completo.
5. Movimento e posizioni persistenti.
6. Magia e consumo delle risorse.
7. Combattimento integrato.
8. NPC persistenti e relazioni.
9. Quest.
10. Save/load completo.
11. Packaging per Steam e gestione del modello AI.

---

## 20. Regola architetturale fondamentale

L'IA non deve diventare la fonte di verità del gioco.

L'IA è responsabile principalmente di:

- interpretazione narrativa;
- descrizione;
- dialoghi degli NPC;
- atmosfera;
- costruzione locale del mondo;
- conseguenze narrative.

Il Game Engine deve essere responsabile di:

- HP;
- stamina;
- mana;
- inventario;
- statistiche;
- abilità;
- magia;
- posizione;
- flag;
- effetti;
- combattimento;
- altri dati meccanici persistenti.

Questa separazione è la base per rendere il progetto stabile e, in futuro, trasformarlo in un gioco distribuibile.


## Integrazione narrativa completata - 22 settembre 2026

Il turno narrativo ora segue un flusso a tre fasi:
1. L'AI interpreta l'intento del PLAYER.
2. Il Game Engine valida ed esegue l'azione reale.
3. Una seconda chiamata AI racconta esclusivamente il risultato dello stato aggiornato.

Sono inoltre integrati:
- recupero delle memorie per rilevanza sul messaggio corrente;
- memoria individuale degli NPC;
- stato persistente degli NPC;
- effetti sociali limitati e validati dall'engine;
- aggiornamento di fiducia, affetto, rispetto e ostilità;
- memorie importanti degli NPC;
- quest persistenti con obiettivi e stato;
- movimento vincolato alle località e alle rotte realmente presenti nel mondo;
- destinazioni non più create automaticamente da un intent AI;
- destinazioni raggiungibili esposte nel CONTEXT;
- cronologia degli eventi del mondo;
- persistenza del mondo separata dalla cronologia chat.

### Regola architetturale finale

L'AI interpreta e narra. Il Game Engine decide ciò che diventa realmente vero.

Il PLAYER controlla il proprio personaggio.
Il mondo è persistente.
Ogni NPC possiede una propria memoria e conoscenza.
Le relazioni cambiano solo tramite effetti validati.
Le quest restano nel salvataggio.
Le informazioni non vengono considerate globalmente conosciute solo perché il modello le conosce.

### Da completare prima di una distribuzione commerciale

Restano attività di prodotto, non correzioni concettuali del sistema narrativo:
- UI dedicata per memoria/inventario/combat; la chat ora mostra stato e quest attive;
- installer e packaging desktop/Steam;
- provider AI locale integrato senza installazione manuale di Ollama;
- test end-to-end su una storia lunga;
- bilanciamento delle regole di combattimento, magia ed economia;
- contenuti iniziali del mondo.
