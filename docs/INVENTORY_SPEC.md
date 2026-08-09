# AI RPG — Inventory Specification

## Obiettivo
L'inventario rappresenta ciò che il personaggio possiede e ciò che sta utilizzando. Deve essere persistente e flessibile.

## Categorie
- Armatura/equipaggiamento difensivo
- Armi
- Oggetti comuni
- Oggetti importanti o speciali
- Materiali/risorse
- Oggetti conservati in contenitori o depositi

## Armatura
Ogni pezzo può contenere:
- nome;
- slot;
- tipo;
- materiale;
- condizioni/durabilità;
- protezione;
- proprietà speciali;
- difetti/danneggiamenti.

La protezione può essere articolata per tipo o zona quando il sistema ne ha bisogno. Non deve essere obbligatoriamente un singolo numero.

## Oggetti
Gli oggetti possono avere dati diversi in base alla loro natura. Non bisogna imporre gli stessi campi a ogni oggetto.

Un oggetto può quindi avere quantità, peso, valore, stato, proprietà, utilizzo, origine, effetti o altri dati pertinenti.

## Persistenza
Quando un oggetto diventa realmente parte dell'inventario del personaggio, il game engine ne aggiorna lo stato nel database. Le modifiche a condizioni, quantità, equipaggiamento e proprietà devono essere persistenti.

## Regola
L'IA non assegna direttamente valori arbitrari all'inventario. Il game engine applica e valida le modifiche richieste dalla simulazione.
