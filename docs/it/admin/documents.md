# Gestire i documenti

La raccolta documenti permette di dare all'AI accesso ai file della tua istituzione — regolamenti, manuali, schede di riferimento — senza doverli incorporare nei prompt di ogni singolo Gem.

## Caricare un documento

1. Apri la scheda **Documenti** nel pannello amministratore.
2. Seleziona una cartella di destinazione (o creane una nuova).
3. Clicca **Carica** e scegli un file.

I formati supportati includono PDF, Word (`.docx`), testo normale e la maggior parte dei formati Office comuni. Trove converte i file caricati in testo normale usando [Markitdown](https://github.com/microsoft/markitdown). Il file originale viene conservato insieme alla versione convertita.

Dopo il caricamento, l'AI genera automaticamente una descrizione di una riga del documento. Questa descrizione è mostrata nel pannello amministratore e viene usata quando l'AI decide quali documenti consultare.

## Cartelle

I documenti sono organizzati in cartelle. Le cartelle sono l'unità di controllo degli accessi: quando crei un Gem, concedi l'accesso a intere cartelle o a singoli documenti al loro interno.

Per creare una cartella, digita un nome nel campo **Nuova cartella** e premi Invio (o il pulsante aggiungi).

Per rinominare una cartella o un documento, clicca sul suo nome nel pannello amministratore.

## Come l'AI usa i documenti

Quando un Gem ha accesso ai documenti, Trove fornisce all'AI un riepilogo di tutti i documenti accessibili prima di iniziare. L'AI può quindi richiedere il testo completo di qualsiasi documento che ritenga rilevante. Non c'è ricerca vettoriale — l'AI ragiona dai riepiloghi e recupera il contenuto completo su richiesta.

Questo significa:
- **Documenti brevi, ben denominati e con buone descrizioni** sono più facili da trovare e usare per l'AI.
- **Documenti molto lunghi** potrebbero essere troncati per rientrare nella finestra di contesto del modello.
- L'AI non usa sempre i documenti — li usa solo quando sembrano rilevanti per la richiesta dell'utente.

## Rimuovere un documento

Clicca il pulsante **Elimina** accanto a un documento nel pannello amministratore. Il file e i suoi metadati vengono eliminati definitivamente.
