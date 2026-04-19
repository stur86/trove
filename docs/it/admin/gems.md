# Gestire i Gem

Un **Gem** è un'attività AI riutilizzabile con uno scopo preciso. Gli utenti vedono i Gem come schede nella schermata principale e compilano un breve modulo per eseguirli.

## Creare un Gem

1. Apri la scheda **Gem** nel pannello amministratore.
2. Clicca **Nuovo Gem**.
3. Compila il modulo:

| Campo | Cosa fa |
|---|---|
| **Nome** | Mostrato sulla scheda del Gem. Tienilo breve e descrittivo. |
| **Descrizione** | Facoltativa. Un suggerimento di una riga mostrato sotto il nome. |
| **Colore** | Il colore dell'icona del Gem. Usa colori diversi per distinguere i Gem a colpo d'occhio. |
| **Template del prompt** | L'istruzione per l'AI. Usa segnaposto `{{ nome_variabile }}` per i campi che l'utente compila. |
| **Funzionalità** | Spunta *Accetta immagini* se il task richiede una foto o uno screenshot. |
| **Modalità output** | *Testo* per output semplice; *Strutturato (JSON)* per output leggibile da macchine. |
| **Accesso ai documenti** | Quali cartelle o singoli file di documenti l'AI può leggere durante l'esecuzione del Gem. |

4. Clicca **Crea**.

## Scrivere un buon template di prompt

Il template è l'istruzione che riceve l'AI. Può includere qualsiasi testo, più segnaposto:

```
Riassumi il seguente testo in {{ lingua }}, usando non più di 5 punti elenco:

{{ testo }}
```

Questo crea due campi di input per l'utente: *lingua* e *testo*.

**Consigli:**

- Sii specifico. Indica all'AI esattamente il formato che desideri.
- Specifica la lingua dell'output atteso, se è importante.
- Tieni le istruzioni brevi — il modello funziona meglio con prompt chiari e concisi.
- Prova tu stesso il Gem prima di condividerlo con gli utenti.

## Accesso ai documenti

Ogni Gem può avere accesso a una parte della raccolta documenti tramite l'albero di cartelle e documenti nel modulo del Gem:

- **Accesso alla cartella** — spunta la casella accanto al nome di una cartella. L'AI può vedere tutti i documenti della cartella, inclusi quelli aggiunti in seguito. Spuntare una cartella seleziona automaticamente tutti i documenti al suo interno.
- **Accesso ai singoli documenti** — espandi una cartella e spunta solo i documenti specifici desiderati. Una cartella con solo alcuni documenti selezionati mostra un indicatore parziale (−).
- **Nessun accesso** (predefinito) — lascia tutte le caselle deselezionate. L'AI non usa la raccolta documenti per questo Gem.

Quando un Gem ha accesso ai documenti, l'AI decide autonomamente se consultarli o rispondere dalle proprie conoscenze.

## Modificare ed eliminare

Clicca **Modifica** accanto a qualsiasi Gem per cambiarne le impostazioni. Clicca **Elimina** per rimuoverlo definitivamente. Non è possibile annullare l'operazione.

!!! warning "Eliminare un Gem"
    I Gem eliminati non possono essere recuperati. Gli utenti che provano ad aprire l'URL di un Gem eliminato vedranno un errore.
