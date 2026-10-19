# ONDA/1.0 — specifica

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

> **Nuova implementazione, non un protocollo ritrovato.** Al 19/10/2026 nessun
> ramo, PR, issue o file Drive conteneva una specifica ONDA, un validatore
> ONDA, Redis o un documento DS223 (ricerca eseguita su 20 rami di tre
> repository e su Drive). L'autore ha autorizzato il 19/10/2026 a usare il suo
> incarico operativo come specifica iniziale ufficiale. Questo file è quella
> specifica, scritta prima del codice. Ogni documento precedente che citi
> «ONDA» come esistente va letto come aspirazione, non come stato.

ONDA è un bus di messaggi firmati su Redis Pub/Sub per far comunicare i nodi
R³∞ (PC Windows, NAS Synology DS223) e gli agenti SDQ-1.

---

## 1. Architettura

```
 controllo (CLI)  ──firma──►  Redis  ◄──firma──  agente RAFFA-001 (processo)
 python -m onda               pub/sub            └─ adattatore → sdq1.agents.raffa.run
 comando / richiesta          + chiavi           agente SENTIN-004 → sentin.run
 stato / verifica                                agente MEMO-002   → memo.run + VectorStore
                                                 monitor (rileva offline)
```

- **Redis** è solo trasporto e stato condiviso. Non è un confine di fiducia:
  la password Redis protegge dall'esterno, le **firme Ed25519** dicono chi ha
  parlato. Chi ha la password Redis può disturbare (cancellare chiavi,
  pubblicare rumore), ma non può firmare a nome di un altro.
- **Un processo per agente.** Ogni agente ONDA è un processo
  `python -m onda agente <ID>`, con una sua chiave privata.
- **Pub/Sub non è memoria.** Ciò che deve sopravvivere (STOP, PAUSA) non sta
  nel canale ma in copie persistenti dello stesso envelope firmato: chiave
  Redis con AOF e copia locale dell'agente (§4).

### 1.1 Agenti reali e adattatore — la differenza da non nascondere

RAFFA-001, MEMO-002 e SENTIN-004 **nella pipeline SDQ-1 non sono processi**:
sono funzioni `run(ctx)` chiamate in sequenza da `sdq1/agents/pipeline.py`
dentro un solo processo, su un `Context` condiviso. Non hanno ciclo di vita,
non possono ricevere messaggi, non possono essere «offline».

ONDA non cambia questo. `onda/adattatore.py` è un **adattatore esplicito**:
un processo ONDA che, per ogni RICHIESTA, costruisce un `Context` nuovo e
chiama **la stessa funzione** della pipeline, poi restituisce il campo che
quella funzione ha scritto:

| Agente | Funzione reale | Corpo della risposta |
|---|---|---|
| RAFFA-001 | `sdq1.agents.raffa.run(ctx)` | `{"intent": ctx.intent}` |
| SENTIN-004 | `sdq1.agents.sentin.run(ctx)` | `{"manipulation": ctx.manipulation}` |
| MEMO-002 | `sdq1.agents.memo.run(ctx, VectorStore)` | `{"memory_hits": ctx.memory_hits}` |

Conseguenze dichiarate:

- La pipeline `python -m sdq1` resta identica e **non usa ONDA**.
- MEMO-002 via ONDA **legge soltanto** la memoria (`retrieve`), non chiama mai
  `add`: un bus che scrive nella memoria vettoriale rifarebbe il loopback di
  CLAUDE.md §4.
- «Agente online» significa: il processo adattatore è vivo e risponde. Un
  heartbeat dice che il processo gira; **solo una RICHIESTA con RISPOSTA
  corretta dice che l'agente funziona** (`python -m onda verifica` fa questo).

## 2. Envelope

JSON UTF-8, un oggetto, al massimo **16 384 byte** serializzato.

| Campo | Tipo | Regola |
|---|---|---|
| `onda` | str | esattamente `"1.0"` |
| `id` | str | 32 caratteri esadecimali (uuid4) |
| `tipo` | str | `HEARTBEAT`, `RICHIESTA`, `RISPOSTA`, `COMANDO`, `EVENTO`, `ERRORE` |
| `mittente` | str | ID nodo, regex `^[A-Z][A-Z0-9]{1,15}-[0-9]{3}$` |
| `destinatario` | str | ID nodo oppure `"*"` |
| `epoch` | int ≥ 0 | epoch globale al momento dell'invio |
| `ts` | float | istante Unix di emissione |
| `scadenza` | float | `ts < scadenza ≤ ts + 300` |
| `correlazione` | str/null | obbligatoria per `RISPOSTA` ed `ERRORE`: l'`id` della richiesta |
| `corpo` | object | contenuto, dipende dal tipo |
| `firma` | str | Ed25519 in base64 sulla forma canonica |

**Forma canonica:** l'envelope senza `firma`, serializzato con chiavi
ordinate, separatori `(",", ":")`, `ensure_ascii=False`, in UTF-8.

### 2.1 Validazione, in quest'ordine (il primo errore vince)

1. dimensione ≤ 16 384 byte, JSON valido, oggetto;
2. campi esatti (né mancanti né in più) e tipi;
3. mittente nel portachiavi, firma valida con la sua chiave pubblica;
4. tempo: `ts` non oltre 30 s nel futuro, `scadenza` non passata;
5. autorizzazione (§5);
6. epoch: `epoch ≥ epoch globale corrente`;
7. destinatario: `destinatario` è il nodo ricevente oppure `"*"`;
8. idempotenza: `id` non già visto **da questo ricevente** (`SET NX` fino alla
   scadenza). Per ricevente, perché un messaggio a `"*"` arriva a più nodi e
   ognuno deve poterlo accettare una volta.

Il limite di frequenza (§5) si applica fra il passo 3 e il 6: dopo la firma,
così un falso non consuma il ritmo di un mittente vero.

Un envelope rifiutato **non produce risposta** (rispondere a un falso darebbe
a chi lo invia un oracolo) e viene registrato nel log con il motivo.

## 3. Canali e chiavi Redis

| Nome | Uso |
|---|---|
| `onda:a:<ID>` | canale: casella di un nodo (richieste, comandi, risposte) |
| `onda:tutti` | canale: messaggi con `destinatario = "*"` |
| `onda:hb` | canale: heartbeat |
| `onda:epoch` | int: epoch globale |
| `onda:visto:<ricevente>:<id>` | idempotenza, scade con l'envelope |
| `onda:agente:<ID>` | hash: `stato` (in chiaro, solo indicativo) e `hb` (l'ultimo heartbeat firmato) |
| `onda:incarnazione:<ID>` | int: cresce a ogni avvio del processo |
| `onda:comando:<ID>`, `onda:comando:*` | ultimo COMANDO firmato, persistente |
| `onda:lock:<nome>` | lock distribuiti |
| `onda:ritmo:<ricevente>:<ID>:<secondo>` | contatore per il limite di frequenza |

## 4. Stati e ciclo di vita dell'agente

```
avvio ──► (legge onda:comando) ──► FERMATO?  sì ──► esce, codice 3
                                       │ no
                                       ▼
            ┌──── PAUSA ────┐    ATTIVO ◄─── RIPRENDI ───┐
            ▼               │       │                    │
        IN_PAUSA ───────────┴───────┴──── STOP ──► FERMATO, esce codice 0
```

- **ATTIVO** — risponde alle RICHIESTE.
- **IN_PAUSA** — continua heartbeat e comandi; alle RICHIESTE risponde
  `ERRORE {"codice": "IN_PAUSA"}`.
- **FERMATO** — il processo termina. Al riavvio, se l'ultimo comando
  persistente è STOP, il processo **non parte** (codice 3) finché un
  controllo non invia RIPRENDI. Questo è il freno d'emergenza: sopravvive
  ai riavvii.
- **OFFLINE** — stato osservato, non dichiarato dall'agente: l'ultimo
  heartbeat in `onda:agente:<ID>` è scaduto (TTL = 3 intervalli = 30 s) o
  non ha una firma valida. Si legge **solo l'envelope firmato**: il campo
  `stato` dell'hash è in chiaro e chi ha la password Redis potrebbe cambiarlo.

**Comandi persistenti — dove vive lo STOP.** Pub/Sub non conserva niente:
un messaggio pubblicato mentre l'agente è giù è perso. Per questo un COMANDO
non vive nel canale ma in tre copie, tutte dello **stesso envelope firmato**:

| Copia | Dove | Sopravvive a |
|---|---|---|
| canale | `onda:a:<ID>` / `onda:tutti` | niente: serve solo all'agente online |
| Redis | chiave `onda:comando:<ID>` / `onda:comando:*`, AOF su disco | riavvio di agente, Redis, NAS |
| locale | `$ONDA_STATO_DIR/<ID>.comando.json`, scritta dall'agente con `fsync` | **anche alla perdita del volume Redis** |

Il controllo scrive la chiave Redis **prima** di pubblicare. L'agente scrive
la copia locale appena riceve il comando, e di nuovo all'avvio se Redis ne ha
uno più recente. All'avvio vale il più recente per `ts` fra le tre fonti
valide; ognuna si ri-verifica (firma del controllo, epoch), non la scadenza:
uno STOP non scade.

**L'autorità è la firma, non lo storage.** Nessuna delle copie è una fonte
indipendente: valgono perché sono firmate dalla chiave `controllo`, che sta
sul PC. Conseguenze, ciascuna coperta da un test:

- chi può scrivere su Redis o sul volume può **cancellare** un comando, non
  **falsificarlo** né sostituirlo con un RIPRENDI;
- senza `ONDA_STATO_DIR` (sviluppo sul PC) uno STOP **non** sopravvive alla
  perdita dei dati Redis — limite dichiarato e provato da un test;
- con `ONDA_STATO_DIR` impostato ma non scrivibile l'agente **non parte**
  (codice 2): meno protetto di quanto dichiarato non è accettabile;
- dopo `epoch --avanza` tutte le copie con epoch vecchio smettono di valere.

**Istanza unica.** Ogni agente tiene il lock `onda:lock:istanza:<ID>` (TTL 3
intervalli, rinnovato a ogni heartbeat). Una seconda istanza con lo stesso ID
non parte (codice 4).

**Heartbeat.** Ogni **10 s** (`ONDA_HB_SECONDI`, sovrascrivibile solo per i
test). Corpo: `{"stato", "incarnazione", "pid", "host"}`.

**Recupero dopo errore Redis.** Connessione persa → l'agente riprova con
attesa crescente (1, 2, 4… max 30 s). Nel frattempo l'ultimo heartbeat scade e il
monitor lo vede OFFLINE: è corretto, l'agente non è raggiungibile. Al rientro
riprende il lock e rilegge il comando persistente.

## 5. Autorizzazioni

Il portachiavi (`portachiavi.json`, pubblico) assegna a ogni ID una chiave
pubblica e un **ruolo**:

- `agente` — processo con heartbeat che serve richieste;
- `controllo` — l'unico che comanda e avanza l'epoch. La sua chiave privata
  **resta sul PC**, mai sul NAS;
- `osservatore` — interroga ed emette eventi (monitor, `verifica` sul NAS),
  non comanda. Aggiunto durante il collaudo del 19/10: registrare il monitor
  come `agente` lo faceva risultare sempre «offline», e `verifica` falliva
  per un agente che non esisteva.

| Tipo | Chi può inviarlo | Vincoli |
|---|---|---|
| HEARTBEAT | solo agente | solo su `onda:hb`, `destinatario = "*"` |
| RICHIESTA | chiunque registrato | destinatario specifico |
| RISPOSTA / ERRORE | chiunque registrato | `correlazione` obbligatoria |
| COMANDO | **solo controllo** | `corpo.azione ∈ {STOP, PAUSA, RIPRENDI}` |
| EVENTO | chiunque registrato | — |

Limite di frequenza: **50 envelope al secondo per mittente**, contati in
ricezione; oltre, scartati e registrati.

## 6. Epoch

`onda:epoch` è un intero che solo un controllo fa avanzare
(`python -m onda epoch --avanza`). Ogni envelope con epoch inferiore viene
rifiutato. Serve dopo un incidente (chiave compromessa e sostituita, comandi
in volo da invalidare): un comando persistito con epoch vecchio smette di
valere, compreso uno STOP — dopo aver avanzato l'epoch va reinviato se serve.

## 7. Lock distribuiti

`SET onda:lock:<nome> <token> NX PX <ttl>`; rilascio e rinnovo solo con lo
stesso token, con script Lua atomico (confronta-e-cancella,
confronta-e-estendi). Un lock scaduto è libero: chi lo teneva lo scopre al
rinnovo successivo, che fallisce.

## 8. Regole di sicurezza

1. **Nessun segreto nel repository.** Chiavi private in una cartella fuori
   (default `~/.r3/onda/`, permessi 0600). Password Redis da
   `ONDA_REDIS_PASSWORD` o `ONDA_REDIS_PASSWORD_FILE`.
2. **Redis senza password non è accettato**: il client rifiuta di connettersi
   senza password, salvo `ONDA_REDIS_SENZA_PASSWORD=1` dichiarato a mano.
3. **Redis mai esposto a Internet.** Nel compose del NAS Redis non pubblica
   porte sull'host. Aprirlo alla LAN o a Tailscale è una decisione separata
   dell'autore (vedi `DEPLOY_DS223.md`).
4. Il log non contiene mai password, chiavi né il corpo delle richieste
   (solo id, tipo, mittente, esito, dimensione).
5. Envelope rifiutati: nessuna risposta, solo log.
6. **Una chiave privata per container**: ogni agente monta solo la propria.
   Un container compromesso non firma a nome degli altri.
7. **La chiave `controllo` non vive sul NAS.** Ci entra solo per il tempo del
   collaudo completo (`DEPLOY_DS223.md` §5b), in `/tmp`, e poi si cancella.
8. Dentro la rete Docker il traffico Redis non è cifrato: per questo Redis
   non esce da quella rete, e il PC lo raggiunge solo via tunnel SSH (§6 del
   deploy).

## 9. Criteri di collaudo

Ogni criterio è un test eseguibile. I livelli sono tre e non si scambiano:

- **Collaudato in locale** — test eseguiti e passati in questa sessione di
  sviluppo, con Redis reale e processi reali; per lo stack Docker, con
  `onda/collaudo_docker.sh` su un host Linux x86_64.
- **Pronto per il deploy** — configurazione e procedura scritte
  (`DEPLOY_DS223.md`), senza ancora averle eseguite sul NAS.
- **Verificato sul NAS** — `collaudo_docker.sh` eseguito sul DS223, con
  l'output conservato. **Al 19/10/2026: nessun criterio è a questo livello.**

### 9.1 I sei criteri di accettazione

| Criterio | Test che lo esegue | Livello |
|---|---|---|
| **Persistenza di STOP** — dopo il riavvio nessun agente riprende prima di un RIPRENDI esplicito | `test_c10_stop_sopravvive_al_riavvio`, `test_stop_a_tutti_sopravvive_al_riavvio_di_redis_e_degli_agenti`, `test_stop_sopravvive_alla_perdita_dei_dati_redis`, `test_copia_locale_manomessa_non_vale`; Docker T6 | Collaudato in locale |
| **PAUSA durante down/up** | `test_c13_…`, `test_pausa_sopravvive_a_down_up_completo`; Docker T3 | Collaudato in locale |
| **Riavvio Redis** — riconnessione, heartbeat, nessuna identità duplicata | `test_c14_riavvio_di_redis` (stesso pid e incarnazione, un solo lock, seconda istanza rifiutata); Docker T4 | Collaudato in locale |
| **Heartbeat** — offline entro la soglia (3 × 10 s = 30 s) | `test_c11_kill_9_diventa_offline` (≤ 3 intervalli misurati); Docker T5 con intervallo reale da 10 s | Collaudato in locale |
| **Sicurezza** — nessun segreto nei log, comandi privilegiati autorizzati | `test_sicurezza_nessun_segreto_nei_log_e_comandi_solo_dal_controllo`, `test_comando_falso_ignorato`, `test_osservatore_non_comanda`, C1–C3; Docker T1, T2, T7 | Collaudato in locale |
| **Deploy NAS** — container, volumi, rete, persistenza sul dispositivo reale | `collaudo_docker.sh` sul DS223 | **Pronto per il deploy, non verificato** |

### 9.2 Criteri di dettaglio

| # | Criterio | Test |
|---|---|---|
| C1 | firma alterata, mittente ignoto, campo in più, >16 KiB, scaduto, futuro → rifiutati | unità |
| C2 | COMANDO firmato da un `agente` o da un `osservatore` → rifiutato | unità |
| C3 | Redis rifiuta connessioni senza password (NOAUTH) | Redis reale |
| C4 | stesso envelope due volte allo stesso ricevente → il secondo rifiutato | Redis reale |
| C5 | epoch avanzato → envelope vecchio rifiutato | Redis reale |
| C6 | lock: esclusivo, rilascio solo col token, scade da solo | Redis reale |
| C7 | limite di frequenza oltre 50/s; un falso non consuma il ritmo altrui | Redis reale |
| C8 | RAFFA-001, SENTIN-004, MEMO-002: risposta uguale alla funzione chiamata direttamente | processi + Redis reale |
| C9 | PAUSA → ERRORE IN_PAUSA; RIPRENDI → risponde di nuovo | processi + Redis reale |
| C10 | STOP → esce 0; riavvio → esce 3; RIPRENDI → riparte | processi + Redis reale |
| C11 | `kill -9` → OFFLINE entro 3 intervalli | processi + Redis reale |
| C12 | seconda istanza stesso ID → esce 4 | processi + Redis reale |
| C13 | PAUSA persiste attraverso il riavvio dell'agente | processi + Redis reale |
| C14 | Redis riavviato → agente si riconnette con la stessa identità | processi + Redis reale |
| C15 | STOP sopravvive alla perdita dei dati Redis (copia locale firmata) | processi + Redis reale |
| C16 | sul DS223: `collaudo_docker.sh` tutto PASS | **solo sul NAS** |

### 9.3 Come si riproduce

```bash
pip install -r requirements.txt          # serve anche redis-server nel PATH
python -m pytest -q tests/test_onda_*.py -rs
# -rs mostra i test SALTATI: senza redis-server l'integrazione non conta come passata

ONDA_BASE=/volume1/docker/onda ONDA_CONTROLLO_DIR=<cartella con CONTROLLO-001.key> \
  bash onda/collaudo_docker.sh            # stack Docker, PASS/FAIL per passo
```
