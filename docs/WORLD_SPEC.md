# AI RPG — Specifica del Mondo

## 1. Filosofia generale

Il mondo è autonomo, realistico, persistente e principalmente **player-driven**.

- Il giocatore è il principale motore dei grandi cambiamenti.
- Il mondo può evolversi autonomamente, ma gli eventi autonomi devono avere cause, tempi e conseguenze coerenti.
- L'IA non deve creare eventi importanti soltanto per rendere la storia più movimentata.
- Ogni cambiamento significativo deve poter essere spiegato dalle condizioni del mondo, dalle azioni dei personaggi o dalle azioni del giocatore.
- Gli eventi e le modifiche persistono nel database.

## 2. Conoscenza del mondo e conoscenza dei personaggi

Il sistema distingue la realtà oggettiva del mondo dalla conoscenza individuale dei personaggi.

### World State
Contiene ciò che è realmente vero nel mondo: luoghi, persone, eventi, fazioni, condizioni, segreti, relazioni reali e altri elementi dello stato globale.

### Character Knowledge
Contiene ciò che un determinato personaggio sa o ritiene di sapere.

Un personaggio può:
- conoscere informazioni corrette;
- non conoscere informazioni esistenti nel mondo;
- avere informazioni incomplete;
- credere a informazioni false;
- conoscere segreti solo se li ha scoperti o gli sono stati comunicati.

### Character Memory
Contiene ciò che il personaggio ricorda degli eventi vissuti o appresi.

### Character Beliefs
Contiene convinzioni e interpretazioni personali, che possono essere diverse dalla realtà del World State.

### Scene Context
Contiene ciò che il personaggio può effettivamente percepire o dedurre nella situazione corrente.

L'IA può conoscere il World State quando agisce come motore/narratore, ma quando interpreta un personaggio deve usare la conoscenza, memoria, convinzioni e percezioni disponibili a quel personaggio.

## 3. Struttura flessibile dei luoghi

I luoghi hanno una struttura comune, ma non sono obbligati ad avere tutti gli stessi dettagli.

Il database stabilisce **quali informazioni possono essere memorizzate**, non quali informazioni devono essere sempre presenti.

Esempi di informazioni possibili:

- identità del luogo;
- tipo;
- descrizione;
- posizione;
- caratteristiche ambientali;
- popolazione;
- cultura;
- governo;
- fazioni;
- economia;
- edifici;
- quartieri;
- PNG presenti;
- eventi;
- risorse;
- pericoli;
- segreti;
- informazioni scoperte dal giocatore.

Un villaggio piccolo può quindi avere pochissimi dati, mentre una capitale può svilupparsi con molti elementi collegati.

L'IA non deve riempire campi mancanti inventando dettagli inutili.

## 4. Costruzione progressiva del mondo

Il mondo non viene definito completamente all'inizio.

Un luogo può iniziare con poche informazioni e acquisire dettagli nel tempo.

Esempio:

```text
Villaggio Arken
- posizione conosciuta
- piccolo villaggio
- circondato da boschi
```

Dopo l'esplorazione possono essere aggiunti:

```text
- taverna
- abitanti
- proprietaria della taverna
- commercio con una città vicina
- problema con dei banditi
- vecchia miniera abbandonata
```

Le nuove informazioni vengono salvate e diventano parte permanente del mondo.

La scoperta può avvenire tramite:
- esplorazione;
- dialoghi;
- eventi;
- osservazione;
- conseguenze di azioni precedenti;
- informazioni fornite da PNG;
- altri sistemi di gioco.

## 5. Esplorazione e mappa

Il giocatore può muoversi liberamente. La mappa non è una lista rigida di destinazioni: rappresenta la geografia persistente del mondo.

La posizione fisica deve essere coerente.

Se un personaggio parte da A, raggiunge B e poi torna indietro, il sistema deve riportarlo lungo una geografia coerente verso A. Non può arrivare casualmente in un'altra posizione senza una causa esplicita.

La mappa deve distinguere almeno:

- geografia reale del mondo;
- luoghi conosciuti;
- percorsi conosciuti;
- informazioni conosciute dal giocatore/personaggio.

Un luogo può esistere nel World State anche se non è ancora stato scoperto dal protagonista.

## 6. Geografia: coordinate + collegamenti

La struttura prevista combina due concetti:

### Coordinate
Descrivono la posizione geografica dei luoghi e permettono al motore di calcolare distanze e direzioni.

### Collegamenti
Descrivono i percorsi effettivamente percorribili tra luoghi.

Un collegamento può avere informazioni come:

- origine;
- destinazione;
- distanza;
- tipo di terreno;
- percorso disponibile;
- difficoltà;
- condizioni;
- eventuali ostacoli;
- stato del percorso.

Questo permette che un luogo sia vicino in linea d'aria ma difficile da raggiungere, oppure che un ponte distrutto renda temporaneamente inutilizzabile un percorso.

## 7. Tempo di viaggio

Il tempo di viaggio viene calcolato dal **game engine**, non dall'IA.

Il motore può usare:

- distanza;
- velocità;
- terreno;
- mezzo di trasporto;
- condizioni del personaggio;
- condizioni ambientali;
- soste;
- altri modificatori deterministici.

L'IA riceve il risultato già calcolato e si occupa principalmente della narrazione e dell'interpretazione.

Il tempo trascorso deve essere persistente e potrà influenzare successivamente:

- PNG;
- eventi;
- relazioni;
- condizioni del mondo;
- disponibilità di luoghi e percorsi;
- eventi autonomi.

## 8. Principio architetturale

Quando possibile, le regole deterministiche devono essere gestite dal codice e non delegate all'IA.

Il codice deve occuparsi di:
- stato persistente;
- coordinate;
- distanze;
- tempo;
- validazione;
- collegamenti geografici;
- consistenza dei dati;
- applicazione delle conseguenze deterministiche.

L'IA deve occuparsi principalmente di:
- interpretazione delle intenzioni;
- narrazione;
- dialoghi;
- comportamento dei personaggi;
- valutazione narrativa delle situazioni;
- generazione di contenuti quando realmente necessario.

Questo documento è una specifica iniziale e verrà esteso man mano che vengono definite le altre parti del sistema del mondo.
