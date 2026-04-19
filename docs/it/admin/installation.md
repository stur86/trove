# Installazione

Questa guida è per chi installa Trove. Non è richiesta esperienza di programmazione.

## Cosa ti serve

- Un computer con **Linux** (Ubuntu 22.04 o successivo consigliato)
- Almeno **4 GB di RAM** (8 GB o più è meglio)
- Almeno **10 GB di spazio libero su disco**
- Una connessione internet *solo durante l'installazione* — dopo, Trove funziona completamente offline

## Passo 1 — Installa Trove

Apri un terminale ed esegui:

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash
```

Questo scarica l'installer, recupera l'ultima versione di Trove e configura tutto. Richiede alcuni minuti.

!!! tip "Comando non trovato dopo l'installazione?"
    Se vedi `trove: command not found` dopo che l'installer ha terminato, esegui il comando che stampa (qualcosa come `export PATH="$HOME/.local/bin:$PATH"`), poi apri una nuova finestra del terminale.

## Passo 2 — Esegui la procedura guidata di configurazione

Esegui la procedura guidata **sullo stesso computer dove hai installato Trove**. La pagina di configurazione è raggiungibile solo da quella macchina — questo è intenzionale.

```bash
trove setup
```

Poi apri un browser **su quello stesso computer** e vai a:

```
http://localhost:7071
```

La procedura guidata ti guida attraverso sei passi:

1. **Lingua** — scegli la lingua dell'interfaccia
2. **Benvenuto** — conferma l'hardware e cosa installerà Trove
3. **Installa Ollama** — scarica il runtime AI (saltato se già installato)
4. **Scegli un modello** — seleziona un modello Gemma 4; vengono mostrati solo i modelli compatibili con il tuo hardware. Questo passo richiede una connessione internet e può richiedere 10–30 minuti.
5. **Account amministratore** — imposta un nome utente e una password per il pannello admin
6. **Installa servizio** — registra Trove per avviarsi automaticamente all'avvio del computer

Al termine, il dashboard mostra l'indirizzo da dare agli utenti.

## Passo 3 — Dai agli utenti un indirizzo affidabile

Quando Trove si avvia mostra un indirizzo come `http://192.168.1.42:7770`. Gli utenti su altri dispositivi aprono questo indirizzo in qualsiasi browser — nessuna app da installare.

**L'indirizzo può cambiare** a ogni riavvio del server, perché i router assegnano automaticamente gli indirizzi. Se cambia, gli utenti vedranno un errore "sito non raggiungibile".

!!! info "Risolvere con un IP statico"
    Assegnare un indirizzo fisso ("statico") al computer server impedisce che l'indirizzo cambi. Si fa una sola volta, nelle impostazioni del router.

    1. Apri la pagina admin del router — di solito `http://192.168.1.1` o `http://192.168.0.1` (controlla l'etichetta sul router).
    2. Trova la sezione **DHCP**, **LAN** o **Prenotazione IP**.
    3. Trova il server Trove nell'elenco dei dispositivi connessi e assegnagli un indirizzo fisso.
    4. Salva e riavvia il router se richiesto.

    Se hai bisogno di aiuto, chiedi al tuo supporto informatico — è un'operazione di routine.

## Avviare e fermare Trove

Se hai installato il servizio durante la configurazione, Trove si avvia automaticamente all'accensione. Puoi anche controllarlo manualmente:

```bash
systemctl --user status trove    # verifica se è in esecuzione
systemctl --user restart trove   # riavvia
systemctl --user stop trove      # ferma
```

Se hai saltato l'installazione del servizio, avvia Trove manualmente quando necessario:

```bash
trove start
```

Premi `Ctrl + C` per fermarlo. Per mantenere il servizio attivo anche quando nessuno è collegato (utile su un server headless):

```bash
loginctl enable-linger $USER   # configurazione una tantum; potrebbe richiedere sudo
```

## Guida alla scelta del modello

| Modello | RAM minima | Audio | Adatto per |
|---|---|---|---|
| Gemma 4 E2B | 4 GB | Sì | Macchine molto lente, risposte più rapide |
| Gemma 4 E4B | 6 GB | Sì | Bilanciato — impostazione predefinita consigliata |
| Gemma 4 26B | 10 GB | No | Qualità migliore, velocità simile a E4B |
| Gemma 4 31B | 20 GB | No | Qualità massima, richiede una macchina potente |

## Risoluzione dei problemi

**"trove: command not found"**
Esegui `export PATH="$HOME/.local/bin:$PATH"` e riprova. Per renderlo permanente, aggiungi quella riga a `~/.bashrc`.

**La pagina di configurazione non si carica**
Assicurati di essere sullo stesso computer dove hai eseguito `trove setup` e che il comando sia ancora in esecuzione nel terminale.

**Gli altri dispositivi non riescono a raggiungere Trove**
Verifica che `trove start` (o il servizio) sia in esecuzione. Assicurati che tutti i dispositivi siano sulla stessa rete Wi-Fi o cablata. Se l'indirizzo continua a cambiare, imposta un IP statico sul router (vedi Passo 3).

**Il download del modello è molto lento**
Il primo download può richiedere 10–30 minuti a seconda della connessione internet. Avviene solo una volta.
