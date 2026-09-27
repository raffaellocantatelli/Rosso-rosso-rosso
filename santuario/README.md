# Santuario — esportare i grafici Mermaid

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Un comando: ogni blocco ```mermaid di un file markdown diventa SVG, PNG e PDF,
più un PDF unico, un indice HTML e un backup con impronte SHA-256.

```bash
cd santuario && PUPPETEER_SKIP_DOWNLOAD=1 npm install && cd ..   # una volta
python santuario/esporta_grafici.py santuario/santuario-master.md
# opzioni: --formati svg,pdf  --tema dark  --config santuario/mermaid-config.json
#          --solo-estrai (senza Chromium)  --uscita DIR  --senza-backup
```

Risultato in `santuario/grafici/` (ignorato da git: si rigenera dalle sorgenti):
`sorgenti/*.mmd`, `svg/`, `png/`, `pdf/`, `tutti-grafici.pdf`, `index.html`
(si apre con doppio clic), `elenco.json`, `backup/*.tar.gz` + `*.sha256.json`.
Esce con codice 1 e scrive `fallimenti.json` se anche un solo file non si genera.

## Gli ID: una regola, tre fonti

1. `%% G05 · Titolo` come prima riga del blocco — **la più sicura**;
2. altrimenti un titolo markdown che contiene `G05` sopra il blocco;
3. altrimenti l'ordine, e lo script avvisa.

## Cosa non c'è qui

**UNKNOWN:** il contenuto dei 27 grafici G01–G27. Non è in nessun ramo né sul
Drive (cercato il 27/09); sta nella conversazione dove sono nati.
`santuario-master.md` ha i 27 posti già pronti, con ID e titolo: si incolla il
corpo di ogni diagramma sotto la sua riga `%%`. Uno slot lasciato vuoto non viene
disegnato: lo script lo elenca come «da incollare».
`esempio.md` è solo la prova della pipeline, non una ricostruzione.

## Cosa si è imparato dalla guida (verificato eseguendola, 27/09)

| Nella guida | Cosa succede davvero | Qui |
|---|---|---|
| `mmdc -w 2400 -H 1600` | mmdc 12 risponde `unknown option '-w'`: **ogni PNG fallisce** | `--size`, versione fissata in `package.json` |
| numerazione G01, G02… in ordine | G14 e G17 sono tabelle: dal 15° grafico **ogni ID è sbagliato** | ID dal commento `%%` o dal titolo |
| `index.html` con `fetch('elenco.json')` | da `file://` il browser blocca: **indice vuoto** | dati scritti dentro l'HTML |
| `set -e` sul ciclo | si ferma al primo errore, non dice quanti restano | converte tutto, poi riporta |
| «27 grafici × 3 = 81 file» | le tabelle nel suo elenco sono 2 (G14, G17), non 3: sono **25 × 3 = 75** | conta i file reali |
| Chromium da root in container | puppeteer rifiuta senza `--no-sandbox` | config generato |
| comando unico con `open` | `open` esiste solo su macOS; lo script lanciato non esiste ancora nella cartella nuova | — |

Prove: `python -m pytest tests/test_santuario_grafici.py` (senza Chromium).
