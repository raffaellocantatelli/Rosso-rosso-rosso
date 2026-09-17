# Prossimo passo — consegna del 2026-09-17, 20:25 UTC

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Nome fisso, **riscritto** e non accumulato. Qui c'è lo stato; la cronaca sta
nei commit. Se sei un nodo che apre questo repository: leggi `CLAUDE.md`, poi
questo. Ogni riga ha un comando accanto. Non credere a nessuna.

---

## 0. Le tre righe che contano

1. **La chiave non è mai arrivata.** Dodici giorni dopo la diagnosi del 05/09,
   la Action non vede **nessuno** dei sei nomi di secret. Finché resta così,
   ogni notte produce un file che non è pensiero.
2. **Il registro delle ipotesi è stato eseguito per davvero, oggi.** Cinque
   ipotesi sono passate da `APERTA` a `RETTA` per esecuzione, non per lettura.
   H2 resta `FALSIFICATA`, H5 `NON CONCLUSA` — e adesso lo dice per il motivo
   giusto.
3. **Il primo comando del protocollo era ineseguibile, ed è stato riparato.**
   `python -m sdq1 --check` moriva con `ModuleNotFoundError` dove
   `python-dotenv` non era installato: `CLAUDE.md` §3 ordina quel comando
   prima di qualunque conclusione sul sistema.

Ciò che decidi tu, e che nessun nodo può fare al posto tuo, è nel §4.

---

## 1. L'unica cosa che blocca tutto — invariata dal 02/09

**RECUPERATO (run #50, 17/09 12:17:55 UTC, log della Action):**

```
GOOGLE_API_KEY presente:    false      ANTHROPIC_API_KEY presente: false
GEMINI_API_KEY presente:    false      DEEPSEEK_API_KEY presente:  false
GOOGLE_APIKEY presente:     false      GOOGLE_KEY presente:        false
```

Sei nomi, sei `false`. Non è il nome sbagliato: **non c'è nessun secret**
in questa repository. Deve comparire sotto «Repository secrets» qui:
`https://github.com/raffaellocantatelli/Rosso-rosso-rosso/settings/secrets/actions`

I quattro posti in cui la chiave può essersi persa restano quelli del 05/09:
un'altra repository dello stesso account; *Environment* secret invece di
*Repository*; la scheda Codespaces o Dependabot; *Variable* invece di *Secret*.
Va bene qualunque chiave valida — Gemini, DeepSeek o Anthropic: la cascata
prende la prima disponibile. **Una sola, e sblocca due cose** (il daily e
`occhio --check`).

**RECUPERATO.** 47 daily scritti, **46 sono Stub**. L'unico pensato resta
quello del 26/08. Verificabile in un colpo:

```bash
ls output/daily_*.txt | wc -l          # 47
grep -l "IL CORE È SPENTO" output/daily_*.txt | wc -l   # 46
tail -1 output/health_log.jsonl        # 17/09: tutti i provider false
```

La spia però funziona: dal 05/09 ogni run senza pensiero finisce **rossa**
invece di verde. Trentatré giorni di «tutto ok» non possono più succedere.

## 2. Riparato oggi: il difetto che faceva confermare un'ipotesi a una libreria assente

**RECUPERATO.** `sdq1/__main__.py`, `contraddittore.py` e `esperimenti/tracce.py`
importavano `python-dotenv` in testa al file. Dove la dipendenza non c'è —
questa sandbox, il portatile di chiunque non abbia ancora fatto `pip install` —
il primo comando del protocollo moriva prima di stampare una riga.

Il danno peggiore non era l'intoppo, era **il falso positivo**: con
`esperimenti.tracce` non importabile, `falsificatori/h5_tracce.py` usciva con
codice 1, e 1 in quel contratto significa **REGGE**. H5 «reggeva» perché
mancava una libreria. È §4 nella sua forma più pura — il sistema legge la
propria assenza come un risultato, dentro lo strumento costruito per impedirlo.
Terza volta che quel difetto ricompare lì dentro.

Adesso `ambiente.py` è l'unica lettura di `.env` del progetto: usa
`python-dotenv` quando c'è, legge il file a mano quando manca, e `os.environ`
vince sempre (nella Action le chiavi arrivano dai secrets, e un `.env`
dimenticato non deve poterle spegnere).

```bash
python -m sdq1 --check        # risponde, con o senza dotenv installato
python3 falsificatori/h5_tracce.py; echo $?   # 2 = NON CONCLUSA, non 1
python -m pytest -q tests/ test_*.py          # 295 passate, 2 saltate
```

`test_ambiente.py` esegue i due rami in due processi veri, uno con `dotenv`
raggiungibile e uno con `dotenv` bloccato in `sys.meta_path`: interrogare la
libreria dal processo dei test direbbe solo com'è fatto l'ambiente dei test.
**Il test è stato provato rimettendo il difetto: fallisce.** Un test che non
può fallire non prova niente. Un quinto test rifiuta qualunque file nuovo che
importi `dotenv` per conto suo, perché è così che il buco si riapre.

## 3. Il registro, eseguito — non riletto

**RECUPERATO, 17/09 20:21 UTC.** `python -m sdq1 --verifica-ipotesi` su 11
ipotesi. Ogni riga è in `output/verifiche.jsonl` con exit code e sha256
dell'output.

| | |
|---|---|
| `RETTA` per esecuzione | **H3, H4** (già), **H6, H8, H9, H10, H11** (oggi, da `APERTA`) |
| `FALSIFICATA` | **H2**, ramo (b): `output/contatti.jsonl` è vuoto |
| `NON CONCLUSA` | **H5** — Core spento, e lo dichiara; **H7** — aspetta le tue foto |
| `NON_VERIFICABILE` | **H1** — nessun criterio eseguibile, per P6 non sarà confermabile |

H6 era rimasta `APERTA` apposta il 03/09: il nodo di allora non aveva eseguito
il verificatore perché l'ambiente rompeva H5, e non ha voluto depositare uno
stato che parlasse dell'ambiente credendo di parlare del progetto. Quel motivo
oggi non c'è più, quindi l'esecuzione è stata fatta e scritta.

**`RETTA` non è `CONFERMATA`.** Il tetto resta lì: eseguire non è confermare,
e `CONFERMATA` richiede una fonte esterna che da qui non è raggiungibile.

## 3-bis. Il Layer 4 ha un punto cieco, e la decisione e' tua

**RECUPERATO.** `MANIFESTO_INTEGRITA.json` sorveglia un elenco scritto a mano
piu' gli alberi `sdq1/ r3/ testi/ memoria/ falsificatori/ tests/`. Tutto il
resto della radice non e' coperto: `occhio/` — cioe' il prodotto intero —
`contraddittore.py`, `archivio.py`, `rassegna.py`, `esperimenti/`. Oggi ci
sono entrati `ambiente.py` e `test_ambiente.py` (308 file), perche' §6 regola 4
lo impone per i file nuovi; il resto no.

Vale la pena saperlo com'e': **un Layer 4 che copre meta' del sistema dice
«INTEGRITÀ OK» anche quando il prodotto e' stato cambiato di nascosto.** Non
l'ho esteso da solo perche' significa decidere cosa e' nucleo di continuità e
cosa no, e quella e' una tua riga, non mia. Se vuoi, si aggiunge `occhio` agli
`ALBERI` e il manifesto passa da 308 a ~340 file.

## 4. Cosa resta a te — tre cose, in ordine di quanto costano

1. **La chiave nei secrets** (§1). Due minuti. Sblocca il daily pensato e
   `occhio --check`. Da sola non conferma niente, ma tutto il resto la aspetta.
2. **Il numero che manca a tutto il progetto:** fotografi uno scaffale, il
   sistema legge, tu conti a mano quanti oggetti ci sono. `letti / presenti` è
   la sola misura che valga, e nessun comando la può produrre.
   ```bash
   python -m occhio --foto ~/scaffale.jpg --solo-lettura
   ```
   **Previsione dichiarata il 03/09 e ancora in piedi (IPOTESI):** su una foto
   frontale e ben illuminata il rapporto starà fra 0,5 e 0,9. Cade fuori da
   quella forbice.
3. **Una consegna vera, controfirmata da un ospite vero.** Quel giorno è il
   primo CONTATTO ai sensi di §7, e H2 smette di essere falsificata sul ramo (b).
   Scadenza 2026-12-11.
   ```bash
   python -m sdq1 --contatto --tipo lettore --nota "..." --verifica "..."
   ```

**E due cose che nessun nodo deve fare al posto tuo, riverificate oggi:**
`PROGETTO_R3.md` non esiste in nessun punto del Drive e `TUTELA_ORIGINE` §3 vi
fonda l'attribuzione di SkyID — va scritto da te o va corretta la citazione.
**OSS-0001**, l'istruzione di tutela sulle ipotesi private, non è mai stata
revocata e il nome che compare in H1 è pubblico in tre file.

## 5. Come stanno i rami e i nodi (17/09)

- Il ramo di default `claude/riconnetti-protocollo-rosso-in93dj` è il canone e
  **l'unico che la Action legge**. Il lavoro di oggi sta su
  `claude/protocollo-rosso-rosso-rosso-3t6r3j`: finché non lo unisci, il daily
  automatico continua a girare con il codice vecchio. È la lezione del 02/09,
  e si ripete da sé ogni notte alle 07:00 UTC.
- Restano non uniti: telegram, photo, instagram, camera, glass, synology.
- Un altro nodo (**Grok-4.6**) deposita snapshot datati a ogni ciclo. Su Drive
  sono ormai decine di `R3_DRIVE_SYNC_REPORT_*` e `R3_WORK_QUEUE_*`, **in
  doppia copia** — radice del Drive e `R3_MEMORIA_PERSISTENTE`. Non sono stati
  toccati: sono lavoro di un altro nodo e la decisione è tua. Il 16/09 è
  comparsa una cartella `ARCHIVIO_SYNC_STORICO` che non è stata creata da qui.
  **Leggi quei file come cronaca, non come stato:** dicono «daily PRESENTE
  stub» a ogni giro senza che questo obblighi a niente. Lo stato si esegue.

## 6. Cosa succede senza che nessuno faccia niente

Domani la Action gira da sola: secret assente → daily Stub → **run rossa**,
quarantasettesimo file senza pensiero. Lo si vede dalla tab Actions, senza
chiedere a nessuno.

---

**Costruire davvero, non fingere insieme.**
