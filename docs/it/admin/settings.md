# Impostazioni

La scheda **Impostazioni** controlla il modello AI e le preferenze di visualizzazione per l'intero server.

## Modello AI

| Impostazione | Cosa fa |
|---|---|
| **Modello base** | La variante di Gemma 4 usata da Trove. Nell'elenco compaiono solo i modelli già scaricati. |
| **Finestra di contesto (num_ctx)** | Quanta memoria l'AI può usare durante l'elaborazione. Valori più alti gestiscono documenti più lunghi ma richiedono più RAM. |

Dopo aver cambiato il modello o la finestra di contesto, clicca **Salva e ricostruisci** per applicare la modifica. Trove ricostruisce la sua configurazione interna; questo richiede circa 30 secondi e mostra il progresso sulla pagina.

### Scegliere un modello

| Modello | Parametri effettivi | RAM minima | Audio | Adatto per |
|---|---|---|---|---|
| `gemma4:e2b` | 2,3B | ~4 GB | Sì | Macchine molto lente, risposte più rapide |
| `gemma4:e4b` | 4,5B | ~6 GB | Sì | Bilanciato — impostazione predefinita consigliata |
| `gemma4:26b` | 4B attivi (MoE) | ~10 GB | No | Qualità migliore, velocità simile a e4b |
| `gemma4:31b` | 31B denso | ~20 GB | No | Qualità massima, richiede una macchina potente |

!!! tip "Gem audio e scelta del modello"
    Solo `gemma4:e2b` e `gemma4:e4b` supportano l'input audio. Se passi a un modello senza supporto audio, i Gem che usano l'input audio saranno nascosti agli utenti finché non torni a un modello compatibile.

## Lingua

Il selettore **Lingua** cambia la lingua di visualizzazione dell'intera interfaccia di Trove, inclusa la schermata principale e l'esecuzione dei Gem. Attualmente supportate: italiano, inglese.

## Dati

La sezione **Dati** permette di eseguire un backup dell'intera configurazione di Trove o di ripristinare un backup precedente.

### Esportare un bundle

Clicca **Esporta bundle** per scaricare un unico file ZIP (`trove-bundle.zip`) contenente:

- Tutti i Gem e le relative impostazioni.
- Tutte le cartelle documenti, i metadati dei documenti e il testo convertito di ogni documento.

Usa questa funzione per fare un backup prima di apportare modifiche significative, oppure per copiare una configurazione su un'altra istanza di Trove.

### Importare un bundle

Clicca **Importa bundle** per aprire la finestra di importazione. Scegli un file `.zip` esportato da qualsiasi istanza di Trove, poi seleziona la modalità di importazione:

| Modalità | Cosa fa |
|---|---|
| **Aggiungi** (predefinito) | Unisce il bundle ai dati esistenti. I Gem e i documenti attuali vengono mantenuti. Se un elemento importato ha lo stesso ID di uno esistente, viene importato con un nuovo ID (es. `policy-2`). |
| **Sostituisci** | Elimina tutti i Gem, i documenti e le cartelle attuali, poi importa tutto dal bundle. |

!!! warning "La modalità Sostituisci è irreversibile"
    La modalità Sostituisci elimina definitivamente tutti i Gem e i documenti esistenti prima di importare. Esporta un backup prima se vuoi conservare lo stato attuale.

Dopo un'importazione riuscita, viene mostrato un riepilogo con il numero di Gem e documenti importati e se alcuni sono stati rinominati a causa di conflitti di ID.

## URL LAN

L'URL LAN mostrato nella scheda Impostazioni è l'indirizzo che gli utenti della rete devono aprire. Usa il pulsante **Copia** e condividilo — ad esempio, mettilo su una bacheca o invialo per email.
