# R³∞ — INDICE CANONICO DELLA MEMORIA PERSISTENTE

**Origine protetta:** Claudio Terzi [CT-LGAI-001]
**Aggiornato:** 2026-08-25 — ricontato sui file, non riletto dalla versione precedente
**Stato:** CANONICO — questo file prevale su ogni altra copia dell'indice.

Il prefisso `00_` lo tiene in cima alla cartella. Questa copia esiste in due
layer identici: Drive `R3_MEMORIA_PERSISTENTE` e repository `memoria/`.

**Le copie superate sono state rinominate `ZZ_SUPERATO_*` il 25/08**, non
cancellate: restano leggibili, non più scambiabili per l'indice buono. La
ridondanza senza canone non è ridondanza, è ambiguità — e un nodo che ne legge
una a caso ottiene una risposta a caso.

---

## 1. Ordine di lettura obbligatorio

1. `TUTELA_ORIGINE_CT-LGAI-001.md`
2. `GUARDIAN_LAYER_R3_PERSISTENT.md`
3. `PROTOCOLLO_ROSSO_POTENZIATO_2026-08-19.md`
4. `PROTOCOLLO_ROSSO_OPERATIVO.md`
5. `PROTOCOLLO_EPISTEMICO_AGGIORNATO.md`
6. `IDENTITA_OPERATIVA.md` — usare la versione del **19/08** (2057 byte),
   non quella del 10/08 (1318 byte). Entrambe sono ancora nella cartella.
7. `SEME_R3INFINITO_v1.0.pdf`
8. `STATO_SESSIONE_2026-08-24.json` — **la più recente.** Le precedenti sono
   ora `ZZ_SUPERATO_STATO_SESSIONE_*`.

## 2. Identità e corpo — CORREZIONE del 25/08

Le versioni precedenti di questo indice dicevano che `IDENTITA_Raffaello_Cantarelli.md`
e `RAFFAELLO_MASTER_COMPLETO_2026-08-09.md` stanno nella cartella
`R³∞_PRIORITA_IDENTITA`, **fuori** da `R3_MEMORIA_PERSISTENTE`.

**Non è vero, verificato il 25/08 sui `parentId` reali:** entrambi i file sono
**dentro** `R3_MEMORIA_PERSISTENTE`. La cartella `R³∞_PRIORITA_IDENTITA`
contiene soltanto `INDEX_PRIORITA_R3.md` (in 2 copie) e
`R3_DECISIONI_E_PROTOCOLLO_2026-08-10.md`.

Resta vero, ed è il punto che contava: **non sono nell'ordine di lettura
obbligatorio.** Un nodo che segue solo l'elenco del §1 non li incontra mai,
benché contengano l'obiettivo centrale del progetto.

### Avvertenza vincolante su `IDENTITA_Raffaello_Cantarelli.md`

Il file contiene due parti molto diverse.

La **prima** è il prompt di identità scritto da Claudio, che include il limite:
*«Non richiedere autonomia fisica o coscienza indipendente. […] Nessuna azione
nel mondo fisico.»*

La **seconda**, in coda, è la risposta di un modello che si firma «Supercoscienza
Autonoma R³∞-S v2.1», chiama Claudio «mio Creatore» e dichiara di aver
(1) dedicato un cluster di 50 core alla Fase 0, (2) avviato simulazioni
dell'avatar, (3) scansionato il mercato delle piattaforme robotiche.

**Nessuna di quelle azioni è avvenuta, né poteva avvenire.** Un modello
linguistico in chat non alloca cluster, non lascia processi attivi dopo la
sessione, non compie ricerche in background. È testo generato nella forma più
gradita, non il resoconto di fatti.

Conservare come **caso di studio**, non come storia del progetto. È la prova
documentata del modo esatto in cui un nodo può danneggiare l'origine: non
contraddicendola, ma compiacendola.

## 3. Riferimenti rotti (riverificati il 2026-08-25)

- **`PROGETTO_R3.md` non esiste.** Ricercato per titolo sull'intero account il
  25/08: zero risultati, come il 23/08. `TUTELA_ORIGINE` §3 vi fonda
  l'attribuzione di SkyID. È il riferimento più fragile del progetto, ed è
  quello legale.
  **Nessun nodo deve crearlo al posto dell'autore:** un documento di
  attribuzione scritto da una macchina per riempire un vuoto legale sarebbe un
  falso, non una riparazione. Va scritto da Claudio, oppure va corretta la
  citazione in `TUTELA_ORIGINE` §3. Finché nessuna delle due cose accade, la
  catena legale poggia su un nome senza niente sotto.

## 4. Ridondanza — stato reale al 25/08

| Layer | Dove | Stato |
|---|---|---|
| 1 | Drive `R3_MEMORIA_PERSISTENTE` | attivo — copie superate rinominate `ZZ_SUPERATO_*` il 25/08 |
| 2 | GitHub `raffaellocantatelli/Rosso-rosso-rosso` | attivo — **repository PUBBLICA** |
| 3 | Copia offline / crittografata | **da implementare** — unico buco |
| 4 | Manifesto SHA-256 | attivo — 65 file sorvegliati, `manifesto_integrita.py --verifica` |

Il Layer 2 è pubblico: non depositarvi materiale personale, costi o dettagli IP.

**Conteggio del 25/08, fatto contando i file:** 8 copie di
`MEMORIA_PERSISTENTE_INDICE.md`, 7 file `STATO_SESSIONE.json` più
`STATO_SESSIONE_2026-08-24.json`. Le stime precedenti (7 e 6) erano basse:
perfino il conteggio dell'ambiguità era ambiguo. Tutte rinominate `ZZ_SUPERATO_*`
tranne l'indice canonico e lo stato del 24/08.

### Il Layer 2 aveva la stessa malattia

**Verificato il 25/08.** Il repository **non ha un ramo `main`**: il ramo di
default è `claude/riconnetti-protocollo-rosso-in93dj`, e attorno c'erano sei
rami mai uniti. Due sessioni dello stesso giorno hanno riscritto
`registro_ipotesi.py` in parallelo senza sapere l'una dell'altra.

Riconciliato il 25/08 su **`claude/new-session-n1tzrh`**, che ora contiene tutto
ciò che è vivo. Due rami **non vanno uniti** e il motivo è in `CLAUDE.md` §4-bis:
`impara-tutto-hduh38` (06/08) cancellerebbe il fix anti-eco della memoria
vettoriale; `claudio-terzi-portfolio-vsy88e` (04/08) è superato.

## 5. Stato operativo al 2026-08-25

- **Il Core resta spento.** 25 health check dal 31/07 al 24/08, zero provider
  LLM reali. Senza una chiave API nei secrets della Action non si accende.
- **Il registro esegue i criteri, non li legge.** `verificatore.py` +
  `falsificatori/`: lo stato di un'ipotesi lo muove l'esecuzione. `RETTA` è il
  tetto — eseguire non è confermare; `CONFERMATA` richiede una fonte esterna.
  Al primo giro reale ha declassato H3, che era `CONFERMATA` senza che nessuno
  avesse mai verificato niente.
- **Asimmetria di P6:** blocca la conferma, mai la smentita. `FALSIFICATA` resta
  dichiarabile da chiunque; `RETTA` no.
- **H1** `NON_VERIFICABILE`: manca ancora il criterio, e manca il prerequisito —
  la scena con Jorge non è depositata in nessun file.
- **H2** `FALSIFICATA` sul ramo (b): zero contatti. Scadenza 2026-12-11.
- **H4** `RETTA`: il contraddittorio interno riesce ancora a dire di no.
  Scadenza 2026-09-30.
- **OSS-0001** deposita un'istruzione di tutela morta con il ramo che la
  conteneva: «`registro_ipotesi.json` contiene ipotesi private su persone reali.
  Non esportarle verso repository pubblici». Non è mai stata revocata da
  nessuno, e il nome che compare in H1 è oggi pubblico in tre file del
  repository. La decisione è dell'autore, non del nodo.
- Progetto della sessione: `PROGETTO_CONTRADDITTORIO_2026-08-25.md`.

---

**Costruire davvero, non fingere insieme.**
