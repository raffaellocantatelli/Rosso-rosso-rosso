# ONDA/1.0 sul Synology DS223 — procedura di deploy

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

| Livello | Cosa copre | Al 19/10/2026 |
|---|---|---|
| **Collaudato in locale** | 51 test pytest (Redis 7.0 reale, processi veri) + `collaudo_docker.sh` sullo stesso compose, stessa immagine, stessi percorsi `/volume1/docker/onda/`, su un host **Linux x86_64** | sì — vedi SPEC §9.1 |
| **Pronto per il deploy** | questa procedura, il compose, `redis.conf.esempio`, lo script di collaudo | sì |
| **Verificato sul NAS** | `collaudo_docker.sh` eseguito **sul DS223** con tutti i passi PASS | **no**: nessuna sessione Claude raggiunge il NAS |

I problemi trovati nel collaudo locale sono già corretti qui sotto (§3,
permessi). Ciò che sul NAS può andare diversamente è segnato **IPOTESI** o
**UNKNOWN**: architettura ARM, versione di Docker, `docker compose` v1/v2.

Ogni passo è in sola lettura fino al §3. Dal §3 in poi si scrive solo
dentro `/volume1/docker/onda/`. Nessun passo apre porte, tocca il firewall,
riavvia il NAS o cancella dati.

---

## 1. Prima di tutto: cosa c'è già (sola lettura)

Via SSH sul NAS (DSM → Pannello di controllo → Terminale e SNMP → SSH):

```bash
cat /etc.defaults/VERSION | grep -E 'productversion|buildnumber'
uname -m                                  # IPOTESI: aarch64 (DS223 = Realtek RTD1619B)
sudo docker version --format '{{.Server.Version}}'
sudo docker ps -a
sudo docker ps -a --filter "name=redis"
sudo docker images | grep -iE 'redis|onda'
sudo netstat -tlnp 2>/dev/null | grep -E ':6379|:6380' || echo "nessuno in ascolto su 6379"
df -h /volume1
ls -la /volume1/docker/ 2>/dev/null
```

Incolla l'output nella sessione, **senza password né token**. Due casi:

- **Esiste già un Redis** (un container o una porta 6379 occupata): fermati qui.
  Non va toccato senza sapere chi lo usa. ONDA userà il suo, separato, su una
  rete Docker interna, ma prima va capito l'altro.
- **Non esiste**: si prosegue.

**UNKNOWN finché non lo esegui:** se `docker` risponde. Su DSM 7.2 arriva con
il pacchetto *Container Manager*; se il comando non esiste, il pacchetto va
installato dal Centro pacchetti (azione tua, non automatizzabile).

## 2. Sul PC Windows: chiavi

In PowerShell, nella cartella del repository, sul branch
`claude/synology-redis-verification-i7knrf`:

```powershell
git fetch origin
git switch claude/synology-redis-verification-i7knrf
py -m pip install "redis>=5,<6" "PyNaCl>=1.5,<2"
py -m pytest -q tests/test_onda_envelope.py      # 21 test, non serve Redis

py -m onda chiavi --genera RAFFA-001   --ruolo agente
py -m onda chiavi --genera SENTIN-004  --ruolo agente
py -m onda chiavi --genera MEMO-002    --ruolo agente
py -m onda chiavi --genera MONITOR-001 --ruolo osservatore
py -m onda chiavi --genera CONTROLLO-001 --ruolo controllo
```

Le chiavi finiscono in `%USERPROFILE%\.r3\onda\`, fuori dal repository.
Su Windows i permessi 0600 non hanno effetto: la cartella è protetta solo dal
tuo account utente. **`CONTROLLO-001.key` non lascia mai il PC**: è l'unica
chiave che può dare STOP.

## 3. Sul NAS: cartelle, password, permessi

```bash
sudo mkdir -p /volume1/docker/onda/{data,chiavi,memoria,repo}
# copia locale firmata dell'ultimo comando, una cartella per agente:
# è ciò che tiene fermo uno STOP anche se data/ va persa
sudo mkdir -p /volume1/docker/onda/stato/{RAFFA-001,SENTIN-004,MEMO-002}

# Password Redis generata sul NAS: non passa da chat, mail o repository.
sudo sh -c 'openssl rand -base64 36 | tr -d "\n/+=" > /volume1/docker/onda/redis-password'
sudo chmod 600 /volume1/docker/onda/redis-password
```

Carica con File Station:

| Dal PC | Sul NAS |
|---|---|
| `%USERPROFILE%\.r3\onda\RAFFA-001.key`, `SENTIN-004.key`, `MEMO-002.key`, `MONITOR-001.key`, `portachiavi.json` | `/volume1/docker/onda/chiavi/` |
| `sdq1\memory\store.json` | `/volume1/docker/onda/memoria/` |
| il repository, branch sopra (zip da GitHub, scompattato) | `/volume1/docker/onda/repo/` |
| `onda\redis.conf.esempio` | `/volume1/docker/onda/redis.conf` |

Poi, sul NAS:

```bash
cd /volume1/docker/onda
# la password va dentro redis.conf, senza farla apparire a schermo
sudo sh -c 'sed -i "s/^requirepass .*/requirepass $(cat redis-password)/" redis.conf'
sudo grep -c '^requirepass SOSTITUISCI' redis.conf   # deve stampare 0

# Permessi: trovati sbagliati nel collaudo del 19/10, ecco perché ci sono.
# Redis nel container gira come uid 999 e deve leggere redis.conf;
# gli agenti girano come uid 1000: leggono chiavi, password e memoria,
# e SCRIVONO in stato/. Se stato/ non è scrivibile l'agente non parte (codice 2).
sudo chown 999:999 redis.conf && sudo chmod 600 redis.conf
sudo chown -R 1000:1000 chiavi memoria stato redis-password
sudo chmod 600 chiavi/*.key redis-password
```

## 4. Avvio

```bash
cd /volume1/docker/onda/repo
sudo docker compose -p onda -f onda/docker-compose.ds223.yml up -d --build
```

**UNKNOWN:** se Container Manager offre `docker compose` (v2) o solo
`docker-compose` (v1). Se il primo non esiste, usa il secondo con gli stessi
argomenti. In alternativa: Container Manager → Progetto → Crea → percorso
`/volume1/docker/onda/repo/onda`, sorgente `docker-compose.ds223.yml`.

La prima build scarica `python:3.12-slim` e `redis:7.2-alpine`.
**IPOTESI:** entrambe hanno l'immagine arm64; si falsifica se la build
fallisce con `exec format error` o `no matching manifest`.

## 5. Collaudo sul NAS

### 5a. Controllo rapido — non disturba niente

```bash
C="sudo docker compose -p onda -f onda/docker-compose.ds223.yml"
$C ps                                              # redis (healthy) + raffa sentin memo monitor
$C run --rm --no-deps -T monitor verifica --come MONITOR-001
echo "exit $?"                                     # 0 = tutto VERIFICATO
sudo docker port onda-redis-1                      # vuoto = nessuna porta pubblicata
```

`verifica` controlla dal vivo: Redis raggiungibile, password obbligatoria
(una connessione senza password deve fallire), AOF attivo, e per ogni agente
una richiesta firmata con risposta firmata. RAFFA-001 e SENTIN-004 devono
rispondere **esattamente** come la funzione della pipeline chiamata lì.

### 5b. Collaudo completo — i sei criteri, sul dispositivo reale

**Disturba ONDA, solo ONDA:** mette in pausa, ferma e riavvia gli agenti,
riavvia il suo Redis, fa `down`/`up` del progetto, mette da parte per qualche
minuto `data/` e poi la rimette. Lancialo solo quando decidi tu.

Serve la chiave `CONTROLLO-001` sul NAS **per la durata del collaudo**:

```bash
mkdir -m 700 /tmp/onda-ctl                         # carica qui CONTROLLO-001.key + portachiavi.json
cd /volume1/docker/onda/repo
sudo ONDA_BASE=/volume1/docker/onda ONDA_CONTROLLO_DIR=/tmp/onda-ctl \
  bash onda/collaudo_docker.sh | tee /volume1/docker/onda/collaudo_$(date +%Y%m%d).txt
rm -rf /tmp/onda-ctl                               # la chiave di controllo NON resta sul NAS
```

| Passo | Criterio |
|---|---|
| T1, T2 | Redis con password, nessuna porta pubblicata, agenti che rispondono |
| T3 | PAUSA durante down/up |
| T4 | riavvio di Redis: stessa identità, nessun duplicato |
| T5 | heartbeat: `docker pause` di MEMO-002 → OFFLINE entro 30 s |
| T6 | STOP: nessuno riprende dopo down/up **e** con Redis ripartito vuoto, finché non arriva RIPRENDI |
| T7 | comandi non autorizzati ignorati, nessun segreto nei log |

Il livello «Verificato sul NAS» si raggiunge **solo** con l'ultima riga
`COLLAUDO: tutti i passi PASS` di quel file. Un passo FAIL dice quale criterio
manca sul dispositivo reale: va letto, non ripetuto finché passa.

### Arresto, diagnosi, emergenza

```bash
$C logs --tail 50 raffa                 # una riga JSON per evento
$C logs monitor | grep agente_offline
$C stop raffa sentin memo               # freno meccanico: ferma i container
$C up -d                                # riparte (lo stato PAUSA/STOP persistito resta)
$C down                                 # rimuove i container; i dati in /volume1 restano
```

Il freno ONDA (STOP firmato, che sopravvive ai riavvii) si dà da un nodo con
la chiave `CONTROLLO-001`, cioè dal PC — vedi §6. Dopo uno STOP l'agente esce
con codice 3 e Docker lo riavvia con attesa crescente: ogni riavvio rilegge lo
STOP ed esce senza servire niente. Osservato nel collaudo: 6 riavvii in 8 s,
poi l'attesa cresce. Se il rumore nei log dà fastidio, `$C stop <servizio>`.

## 6. Collegare il PC al bus — decisione tua

Con il compose così com'è, **il PC non raggiunge Redis**: nessuna porta è
pubblicata. È voluto. Per dare comandi dal PC servono due cose, in quest'ordine.

**Raccomandato: tunnel SSH, nessuna porta sulla LAN.** Nel compose, sotto
`redis:`, aggiungere solo:

```yaml
    ports:
      - "127.0.0.1:6379:6379"   # solo loopback del NAS, non la LAN
```

e dal PC:

```powershell
ssh -N -L 6379:127.0.0.1:6379 <utente>@<ip-del-NAS>     # lascia aperta questa finestra
$env:ONDA_REDIS_URL = "redis://127.0.0.1:6379/0"
# la password: copia /volume1/docker/onda/redis-password nella cartella delle chiavi del PC
$env:ONDA_REDIS_PASSWORD_FILE = "$env:USERPROFILE\.r3\onda\redis-password"
py -m onda stato
py -m onda comando PAUSA SENTIN-004 --come CONTROLLO-001
py -m onda verifica --come CONTROLLO-001
py -m onda comando STOP "*" --come CONTROLLO-001        # emergenza: tutti
py -m onda comando RIPRENDI "*" --come CONTROLLO-001
```

Il traffico viaggia cifrato nell'SSH che usi già, e Redis resta invisibile
alla LAN. Le alternative (porta sull'IP di LAN più il firewall DSM, oppure
Tailscale) espongono Redis senza TLS a una rete più ampia: non le preparo
senza una tua richiesta esplicita.

## 7. Ripristino

| Per tornare a… | Comando | Distruttivo? |
|---|---|---|
| nessun container ONDA | `$C down` | no: dati e chiavi restano in `/volume1/docker/onda` |
| nessuno STOP/PAUSA pendente | `py -m onda comando RIPRENDI "*" --come CONTROLLO-001` | no |
| invalidare tutti i comandi in volo e persistiti | `py -m onda epoch --avanza --come CONTROLLO-001` | no, ma gli STOP vanno ridati |
| chiave compromessa | rigenera quella chiave (cancella il `.key`, `chiavi --genera`), ricopia `portachiavi.json`, poi `epoch --avanza` | sì, sulla chiave vecchia: **chiedi prima** |
| nessuna traccia di ONDA sul NAS | `$C down` e cancellare `/volume1/docker/onda` | **sì: solo con tuo consenso esplicito** |

Il ramo di default del repository non è toccato: tutto sta sul branch
`claude/synology-redis-verification-i7knrf`.

**Backup.** `/volume1/docker/onda/data` contiene l'AOF (stato dei comandi);
`chiavi/` contiene chiavi private. Se li includi in Hyper Backup, l'attività
deve essere **cifrata**.
