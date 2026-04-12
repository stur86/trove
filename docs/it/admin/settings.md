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

## URL LAN

L'URL LAN mostrato nella scheda Impostazioni è l'indirizzo che gli utenti della rete devono aprire. Usa il pulsante **Copia** e condividilo — ad esempio, mettilo su una bacheca o invialo per email.
