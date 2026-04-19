# Panoramica amministratore

Il pannello amministratore è accessibile solo dal computer su cui è in esecuzione Trove. Apri `http://localhost:7770/admin` in un browser su quella macchina e accedi con le credenziali impostate durante la configurazione iniziale.

!!! warning "L'accesso admin è solo da localhost"
    Il login amministratore è intenzionalmente nascosto a tutti gli altri dispositivi della rete. Questa è una misura di sicurezza. Per gestire Trove devi essere fisicamente al server, oppure usare un tunnel SSH.

## Le quattro schede

| Scheda | Cosa puoi fare |
|---|---|
| **Impostazioni** | Scegli il modello AI, imposta la dimensione della finestra di contesto, cambia la lingua di visualizzazione |
| **Documenti** | Carica file, organizzali in cartelle, visualizza i riepiloghi generati dall'AI |
| **Gem** | Crea, modifica ed elimina Gem |
| **Log** | Visualizza le ultime 1 000 righe del log del server, aggiornato ogni 5 secondi |

## URL LAN

La scheda Impostazioni mostra l'**URL LAN** — l'indirizzo che gli altri dispositivi devono usare per accedere a Trove. Copialo e condividilo con gli utenti.

## Prossimi passi

- [Installazione](installation.md)
- [Gestire i Gem](gems.md)
- [Gestire i documenti](documents.md)
- [Riferimento impostazioni](settings.md)
