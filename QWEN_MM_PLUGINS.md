# Qwen-MM-Plugins — cosa è vero, e cosa cambia per questo progetto

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Letto alla fonte il 15/09/2026: `README.md`, `install.sh` (89.886 byte),
`.claude-plugin/marketplace.json` e i manifesti di `core`, scaricati da
`raw.githubusercontent.com/QwenLM/Qwen-MM-Plugins`. Il riassunto arrivato in
chat non è la fonte: descrive un repository, e §1 dice che un recupero si
prende dal codice, non da un documento che ne parla.

**Nessun plugin è stato installato.** Questa sessione gira in un contenitore
effimero: installare qui vorrebbe dire dichiarare un potere che sparisce con la
sessione (§2.2). I comandi qui sotto si eseguono sulla macchina di Claudio.

---

## 1. Le affermazioni, una per una

| Affermazione ricevuta | Verdetto |
|---|---|
| Il repository esiste, Apache-2.0, di Alibaba (QwenLM) | **RECUPERATO** |
| Funziona su Claude Code, Codex, Gemini CLI, OpenClaw, Qwen Code, CodeBuddy, Qoder | **RECUPERATO** — l'installatore guidato nomina esattamente questi sette |
| «Nel video 7 capability, nel repo oggi 8» | **FALSO. Oggi sono 11**, e undici sono anche i plugin nel manifesto del mercato |
| `core` non richiede chiave API | **RECUPERATO** — «No API key in the default native mode» |
| Il default è `QWEN_MM_NATIVE_MODE=1` | **RECUPERATO**, ed è il punto che andava controllato davvero (§2) |
| La capability si chiama `vision` | **FALSO**: si chiama `api`. `vision` non esiste |
| `blender` e `freecad` pilotano i programmi già installati | **RECUPERATO** |
| `edu-agent` è solo Skill | **RECUPERATO** — e i video didattici che genera sono **in cinese**, cosa che il riassunto non diceva |
| Comandi di installazione e aggiornamento | **RECUPERATO**, identici carattere per carattere |
| `claude plugin marketplace add …` funziona | **RECUPERATO**: `.claude-plugin/marketplace.json` esiste, il mercato si chiama `qwen-mm-plugins` |
| Account nuovo ≈ 1 milione di token per modello per 90 giorni | **UNKNOWN**: non sta nel repository. È una condizione commerciale di Alibaba, e va letta sulla pagina dell'account |
| Regione Singapore; Pechino e Virginia fatturano dal primo token; la regione non si cambia | **UNKNOWN** dalla stessa fonte. **Non serve deciderlo adesso**: riguarda solo DashScope, e `core` non lo usa |

## 2. Il default che decide se i file escono di casa

```
QWEN_MM_NATIVE_MODE|0|runtime|1|1 returns MCP images; 0 sends images to the VL endpoint and returns captions
```

I campi di quella tabella sono `chiave | segreto | gruppo | default | descrizione`
(letto a riga 1677 dello script, dove viene spacchettata). Quindi il default è
**1**: l'immagine torna al modello che sta già nella sessione, e non parte verso
l'endpoint di Alibaba. Con `0` la fotografia **esce dalla macchina** e torna
indietro come didascalia.

Era l'unica riga da verificare per davvero, perché i due valori fanno cose
opposte e il riassunto non poteva dimostrare quale fosse il default.

## 3. Che cosa fa l'installatore, letto e non dedotto

`curl … | bash` esegue come te uno script di 90 KB che non hai letto. Non è un
motivo per non usarlo — è un motivo per sapere cosa contiene. Letto:

- **nessun `sudo`**, zero occorrenze;
- scrive **solo dentro `$HOME`**: `~/.qwen-mm-plugins/config`, le cartelle degli
  harness (`~/.claude/skills`, `~/.gemini/…`, `~/.qwen/…`), `~/.local/bin`,
  la cache;
- contatta **tre host**: `github.com`, `raw.githubusercontent.com`,
  `astral.sh` (l'installatore di `uv`);
- i server MCP partono con `uvx` da un **tag immutabile**
  (`qwen-mm-plugins-core-v1.1.0`), non da un ramo che può cambiare sotto i piedi.

Chi non vuole `curl | bash` ha la via equivalente e leggibile:

```bash
claude plugin marketplace add https://github.com/QwenLM/Qwen-MM-Plugins.git
claude plugin install qwen-mm-plugins-core@qwen-mm-plugins
```

Serve `uv` (che fornisce `uvx`). `ffmpeg` serve per i video, non per le
fotografie.

## 4. Perché riguarda questo progetto, e fin dove

`PROSSIMO_PASSO` §1-bis dice che **nessun modello ha mai guardato un oggetto
vero**: `occhio` non ha mai avuto una chiave di visione, e il numero che manca a
tutto il progetto è `letti / presenti` — quanti oggetti di uno scaffale
finiscono scritti davvero.

**Quello che `core` sblocca (INFERITO, da verificare eseguendolo):** in una
sessione, il modello vede i pixel della fotografia. Si fotografa uno scaffale,
si chiede l'elenco, si contano a mano gli oggetti presenti. **Il numero si
ottiene oggi, senza chiavi e senza account.**

**Quello che `core` NON sblocca, e va detto:** non dà nessuna API a
`occhio/visione.py`. Il daily, la Action e l'inventario che gira da solo restano
esattamente dove sono — senza chiave. Sono due cose diverse, e il riassunto le
confonde: *un modello che guarda dentro una sessione* non è *un programma che
guarda quando nessuno c'è*.

**La trappola, dichiarata prima di cadercidentro (IPOTESI):** un rapporto
`letti/presenti` misurato con il modello della sessione non si trasferisce al
modello che `occhio` userebbe in produzione. Tarare le soglie sul primo e poi
far girare il secondo significa misurare una cosa e usarne un'altra. Si
falsifica confrontando i due sullo stesso scaffale, il giorno in cui esiste una
chiave.

**E non tocca H2.** È una capacità in più, non un contatto: nessuno si è fatto
vivo perché il sistema vede meglio. §4 resta — a parità di tempo, vale di più
ciò che porta il progetto fuori da sé.

## 5. L'esperimento, e basta quello

Non installare otto capability. Una, quella che questa settimana toglie un
lavoro fatto a mano.

```bash
# sulla macchina di Claudio, una volta sola
claude plugin marketplace add https://github.com/QwenLM/Qwen-MM-Plugins.git
claude plugin install qwen-mm-plugins-core@qwen-mm-plugins
# poi, in Claude Code:  /reload-plugins
```

Poi la misura che PROSSIMO_PASSO chiede da dieci giorni:

```text
@scaffale.jpg   Elenca ogni oggetto che riesci a leggere: tipo e titolo.
```

Si contano a mano gli oggetti nella fotografia, si scrivono i due numeri.
**È l'unica misura che valga**, e la previsione era già stata dichiarata:
fra 0,5 e 0,9 su una foto frontale e illuminata; sotto 0,3 il problema è la
fotografia, non il programma.

Quando il numero c'è, si registra:

```bash
python3 registro_osservazioni.py \
  --annota "letti/presenti su uno scaffale reale: N su M" \
  --strano "atteso fra 0,5 e 0,9 — vedi PROSSIMO_PASSO §1-bis" \
  --contesto "core di Qwen-MM-Plugins, modello della sessione, foto <nome>"
```

(La riga sopra è stata scritta con `--nota`, che non esiste. Eseguito
`registro_osservazioni.py --help` prima di depositarla: le opzioni vere sono
`--annota`, `--strano`, `--contesto`. Un comando inventato dentro un documento
è un'inferenza travestita da recupero, e qui è il difetto che si ripete.)
