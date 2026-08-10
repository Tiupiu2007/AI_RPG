# AI RPG — TODO / Roadmap

## Personaggi
- [ ] Collegare la generazione completa a inventario, denaro e magie.
- [ ] Salvare e caricare in modo strutturato inventario, denaro e magie nel database.
- [ ] Separare definitivamente i moduli backend del personaggio per responsabilità.
- [ ] Gestire equipaggiamento, danni, usura e riparazione.
- [ ] Gestire apprendimento, evoluzione e padronanza delle magie.
- [ ] Collegare livello ed esperienza alla progressione reale.
- [ ] Migliorare la generazione da descrizione libera.

## Mondo
- [ ] Implementare World State persistente.
- [ ] Implementare luoghi a struttura libera e generazione progressiva.
- [ ] Implementare geografia con coordinate + collegamenti.
- [ ] Implementare percorsi, distanze e tempi di viaggio deterministici.
- [ ] Implementare mappa esplorabile e conoscenza separata della mappa.
- [ ] Implementare biomi e transizioni geografiche coerenti.
- [ ] Implementare distribuzione dinamica delle razze con territori di maggiore concentrazione.
- [ ] Implementare popolazione aggregata dinamica per città e insediamenti.

## Conoscenza e narrativa
- [ ] Separare verità del mondo, conoscenza dei singoli personaggi, ricordi e convinzioni.
- [ ] Impedire il metagaming dell'IA nella narrazione.
- [ ] Implementare eventi autonomi con cause, tempi e conseguenze coerenti.
- [ ] Rendere il giocatore la principale fonte dei cambiamenti importanti del mondo.
- [ ] Implementare memoria narrativa persistente e selezione del contesto rilevante.

## Sistema di gioco
- [ ] Integrare tempo globale, calendario e condizioni ambientali.
- [ ] Integrare economia, commercio e valute.
- [ ] Integrare combattimento e conseguenze fisiche.
- [ ] Integrare relazioni e reputazione con il mondo.
- [ ] Integrare salvataggi completi e caricamento affidabile.
- [ ] Aggiungere controlli di consistenza del game engine prima delle modifiche persistenti.

## IA
- [ ] Ridurre al minimo i compiti deterministici affidati all'IA.
- [ ] Separare narratore, interprete dei personaggi e motore del mondo.
- [ ] Definire prompt/context builder separati per ogni responsabilità.
- [ ] Validare sempre le azioni prodotte dall'IA.
- [ ] Gestire errori, output non validi e recupero senza rompere lo stato del mondo.

## Interfaccia
- [ ] Rifinire completamente lo stile generale.
- [ ] Migliorare pannello personaggio e inventario.
- [ ] Creare una schermata mappa.
- [ ] Creare visualizzazione delle magie per categoria.
- [ ] Migliorare ricerca e gestione dei personaggi.
- [ ] Aggiungere indicatori di stato, livello, denaro ed equipaggiamento.
- [ ] Rendere l'interfaccia responsive e coerente tra le sezioni.

## Test e stabilità
- [ ] Test automatici per database personaggi.
- [ ] Test automatici per inventario e denaro.
- [ ] Test automatici per magie.
- [ ] Test automatici per movimento e tempo.
- [ ] Test per salvataggio/caricamento.
- [ ] Test per coerenza della conoscenza dei personaggi.
- [ ] Test end-to-end generazione → salvataggio → caricamento → modifica.

## Ordine consigliato
1. Stabilizzare personaggi + database.
2. Completare inventario/denaro/magie.
3. Costruire World State e geografia.
4. Costruire tempo e movimento.
5. Costruire conoscenza/memoria.
6. Integrare eventi autonomi.
7. Integrare narrativa IA.
8. Rifinire interfaccia e mappa.
9. Test completi e ottimizzazione.


1. Relazioni persistenti
2. Evoluzione delle relazioni
3. Memoria intelligente
4. Stato del mondo
5. Personaggi presenti/ascolto
6. Eventi e conseguenze
7. Sistema di tempo
8. Sistema di luoghi
9. Sistema di obiettivi
10. Rifinitura del comportamento AI
