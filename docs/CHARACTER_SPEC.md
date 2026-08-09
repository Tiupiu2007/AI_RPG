# AI RPG — Character Specification

## Principio
Il personaggio è modulare. I dati vengono separati per responsabilità e il database conserva solo ciò che ha senso conservare.

La generazione deve usare codice per i dati deterministici/regolati e IA solo dove serve creatività, coerenza narrativa o interpretazione.

## Struttura
- Identity: nome, cognome, soprannome, età, data di nascita, sesso, razza, descrizione fisica, aspetto.
- Languages: lingue conosciute e relative competenze.
- Statistics: statistiche di base e valori derivati.
- Current State: salute, energia, condizioni e stato corrente.
- Abilities: capacità e abilità non magiche.
- Knowledge: conoscenze personali, separate dalla verità globale del mondo.
- Talents: talenti e predisposizioni.
- Magic: magie conosciute e apprese.
- Progression: livello, esperienza e crescita.
- Class/Profession: classe, professione o ruolo quando presenti.
- Traits: tratti personali.
- Personality: personalità.
- Mental State: stato mentale ed emotivo.
- Memory: ricordi persistenti.
- Relationships: relazioni con altri personaggi.
- Family: famiglia e legami familiari.
- Background: storia personale e origine.
- Social Status: posizione sociale, reputazione e status.
- Inventory: equipaggiamento e oggetti posseduti.

## Inventario
L'inventario deve distinguere almeno:
- equipaggiamento indossato;
- armatura;
- armi;
- oggetti comuni;
- oggetti importanti o speciali;
- materiali e risorse;
- oggetti eventualmente conservati in contenitori o depositi.

### Armatura
Ogni elemento di armatura può avere:
- nome;
- tipo/slot;
- materiale;
- condizioni/durabilità;
- protezione;
- eventuali proprietà speciali;
- eventuali difetti o danneggiamenti.

La protezione non deve essere necessariamente un singolo valore: il sistema può supportare protezioni diverse quando servono, mantenendo comunque una struttura libera.

## Magia
Il personaggio possiede una sezione persistente per tutte le magie imparate. Le magie sono organizzate per categorie/scuole, ma la struttura deve rimanere estendibile.

Esempio:
- Fuoco
- Acqua
- Aria/Vento
- Terra
- Ghiaccio
- Fulmine
- Luce
- Oscurità
- Vita/Guarigione
- Morte/Negromanzia
- Natura
- Metallo
- Spazio
- Tempo
- Telecinesi
- Illusione
- Evocazione
- Barriere/Protezione
- Potenziamento
- Maledizioni
- Purificazione
- Magia spirituale
- Magia mentale
- Magia dimensionale
- Magia di sangue
- Magia arcana
- Altre scuole eventualmente scoperte nel mondo.

Ogni magia può contenere, quando rilevante:
- nome;
- categoria/scuola;
- descrizione;
- effetto;
- livello/difficoltà;
- costo o consumo di risorse;
- condizioni d'uso;
- grado di padronanza;
- modalità di apprendimento;
- eventuali limitazioni;
- eventuali evoluzioni/varianti.

Non tutte le magie devono avere tutti i campi: la struttura è volutamente flessibile.

## Generazione
Premendo "Genera personaggio", il sistema deve produrre e salvare l'intero personaggio coerentemente con razza, background, statistiche, livello, abilità, inventario, magie, personalità e resto dei dati pertinenti.

Una breve descrizione fornita dall'utente può guidare la generazione. Anche l'IA durante la storia potrà proporre/generare personaggi a partire da una descrizione, ma il risultato deve passare dalle regole del game engine prima del salvataggio.

## Regola fondamentale
Il personaggio deve essere coerente ma non omogeneo: statistiche, abilità, equipaggiamento e magie devono riflettere storia, razza, esperienza, professione, personalità e circostanze. Non tutti i personaggi devono avere gli stessi valori o lo stesso insieme di capacità.
