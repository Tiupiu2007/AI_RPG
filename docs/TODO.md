# TODO AI_RPG

## Stato attuale

Il nucleo narrativo persistente è integrato:
- interpretazione AI -> Game Engine -> narrazione;
- memoria contestuale persistente;
- memoria individuale NPC;
- relazioni e reazioni NPC persistenti;
- mondo e tempo persistenti;
- movimento vincolato alle rotte del mondo;
- quest persistenti;
- combattimento narrativo collegato al combat engine;
- salvataggio dello stato nel database/personaggio.

## Prossime attività di prodotto

Queste non sono fondamenta mancanti, ma attività necessarie per una release completa:
1. test end-to-end su sessioni molto lunghe;
2. bilanciamento di combattimento, magia, stamina e relazioni;
3. UI dedicata a quest, memoria, inventario e stato del mondo;
4. gestione degli errori AI con retry/fallback senza interrompere la partita;
5. packaging desktop/Steam;
6. provider locale integrato per eliminare la dipendenza da un'installazione manuale di Ollama;
7. contenuti iniziali del mondo e NPC.

## Regola

Non aggiungere sistemi narrativi che permettano all'AI di modificare direttamente lo stato autorevole.
