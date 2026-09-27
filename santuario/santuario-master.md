# Santuario — documento master dei grafici

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Struttura dei 27 grafici elencati nella guida del 27/09. **I contenuti non
ci sono ancora**: i grafici sono stati scritti in un'altra conversazione e non
stanno né in questo repository né sul Drive (cercato il 27/09).

**Come riempirlo.** Sotto ogni riga `%% Gnn · Titolo` incolla il corpo del
diagramma (dalla riga `flowchart`, `sequenceDiagram`, … in giù). Lascia la riga
`%%`: è ciò che tiene l'ID giusto. Uno slot lasciato vuoto non viene
disegnato: lo script lo elenca come «da incollare». Poi:

```bash
python santuario/esporta_grafici.py santuario/santuario-master.md
```

**Conteggio corretto.** La guida dice «24 Mermaid e 3 tabelle», ma nel suo
stesso elenco le tabelle sono due (G14, G17): i Mermaid sono **25**, e i file
attesi 25 × 3 = **75**, non 81 né 72.

---

## Analisi iniziale

### G01 · Visione in una mappa

```mermaid
%% G01 · Visione in una mappa
%% tipo atteso: mindmap
```

---

## Disegno progetto

### G02 · La colonia — grammatica funzionale

```mermaid
%% G02 · La colonia — grammatica funzionale
%% tipo atteso: flowchart TB
```

### G03 · Architettura — il luogo ricorda

```mermaid
%% G03 · Architettura — il luogo ricorda
%% tipo atteso: flowchart LR
```

### G04 · Macchina a stati riconciliazione

```mermaid
%% G04 · Macchina a stati riconciliazione
%% tipo atteso: stateDiagram
```

### G05 · Modello dati SQLite

```mermaid
%% G05 · Modello dati SQLite
%% tipo atteso: erDiagram
```

### G06 · Sequenza — silenzio dopo un'azione

```mermaid
%% G06 · Sequenza — silenzio dopo un'azione
%% tipo atteso: sequenceDiagram
```

### G07 · Le prove — due suite, 29 test

```mermaid
%% G07 · Le prove — due suite, 29 test
%% tipo atteso: flowchart TB
```

### G08 · I tredici nuovi casi

```mermaid
%% G08 · I tredici nuovi casi
%% tipo atteso: flowchart LR
```

### G09 · I tre piani da non confondere

```mermaid
%% G09 · I tre piani da non confondere
%% tipo atteso: flowchart TB
```

### G10 · Roadmap H0–H3

```mermaid
%% G10 · Roadmap H0–H3
%% tipo atteso: flowchart LR
```

### G11 · Il confine — provato vs visione

```mermaid
%% G11 · Il confine — provato vs visione
%% tipo atteso: flowchart TB
```

### G12 · La sintesi — una frase per piano

```mermaid
%% G12 · La sintesi — una frase per piano
%% tipo atteso: flowchart TB
```

---

## Invenzioni

### G13 · Pre-mortem 2029

```mermaid
%% G13 · Pre-mortem 2029
%% tipo atteso: flowchart TB
```

### G14 · Tripwire cruscotto

*Tabella, non Mermaid: incolla qui la tabella markdown.*

### G15 · Decision journal timeline

```mermaid
%% G15 · Decision journal timeline
%% tipo atteso: timeline
```

### G16 · Confidence dashboard

```mermaid
%% G16 · Confidence dashboard
%% tipo atteso: flowchart LR
```

### G17 · Role clarity matrix

*Tabella, non Mermaid: incolla qui la tabella markdown.*

### G18 · Question queue

```mermaid
%% G18 · Question queue
%% tipo atteso: flowchart TB
```

---

## Sinergia

### G19 · Registro dei prestiti

```mermaid
%% G19 · Registro dei prestiti
%% tipo atteso: flowchart LR
```

### G20 · Clausola di reversibilità

```mermaid
%% G20 · Clausola di reversibilità
%% tipo atteso: stateDiagram
```

### G21 · Confine poroso

```mermaid
%% G21 · Confine poroso
%% tipo atteso: flowchart TB
```

### G22 · Termometro della sinergia

```mermaid
%% G22 · Termometro della sinergia
%% tipo atteso: flowchart LR
```

### G23 · Diario dell'attrito

```mermaid
%% G23 · Diario dell'attrito
%% tipo atteso: flowchart TB
```

### G24 · Guardiano della sinergia

```mermaid
%% G24 · Guardiano della sinergia
%% tipo atteso: flowchart TB
```

### G25 · Memoria a strati

```mermaid
%% G25 · Memoria a strati
%% tipo atteso: flowchart TB
```

### G26 · Ciclo di riscontro

```mermaid
%% G26 · Ciclo di riscontro
%% tipo atteso: sequenceDiagram
```

### G27 · Sintesi otto meccanismi

```mermaid
%% G27 · Sintesi otto meccanismi
%% tipo atteso: flowchart TB
```
