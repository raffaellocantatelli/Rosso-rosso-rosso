# Opere rivendicate

Autore: **Claudio Terzi**, Bruxelles — origine protetta **[CT-LGAI-001]**.

Questo file è un **registro di paternità**, non una pubblicazione. Dichiara
quali opere esistono e a chi appartengono. Non ne espone il contenuto: ciò che
vive su Drive resta su Drive, e la decisione di pubblicarlo è sempre e solo
dell'autore.

Ogni voce porta un'etichetta epistemica, come tutto il resto del progetto: chi
legge deve poter distinguere ciò che è verificabile qui dentro da ciò che è
dichiarato dall'autore e vive altrove.

---

## Software

| Opera | Dove | Stato |
|---|---|---|
| **R³∞ Framework** — architettura, protocollo epistemico, registro delle ipotesi | questo repository | **RECUPERATO** |
| **SDQ-1** — pipeline multi-agente, router LLM, memoria vettoriale, SAR | `sdq1/` | **RECUPERATO** |
| **R³ Knowledge Redundancy System** | `r3/` | **RECUPERATO** |
| **Osservatorio** — quadro OSINT, fotogramma, posizione astronomica | `osservatorio/` | **RECUPERATO** |
| **Strumenti di integrità** — manifesto, registro nodi, verifica nodo | radice | **RECUPERATO** |
| **UmbraTheater** — piattaforma OSINT geospaziale | [repository separato](https://github.com/raffaellocantatelli/UmbraTheater) | **RECUPERATO** — licenza MIT, distinta da questa |

## Testi

| Opera | Dove | Stato |
|---|---|---|
| **Il Protocollo Rosso Rosso Rosso** — opera compiuta: prefazione, quattro capitoli, conclusione | Drive | **DICHIARATO** dall'autore |
| **Il Destinatario** | `testi/IL_DESTINATARIO.md` | **RECUPERATO** |
| **Protocollo Rosso v2 — revisione** | `testi/PROTOCOLLO_ROSSO_v2_REVISIONE.md` | **RECUPERATO** |

## Entità progettate

| Opera | Dove | Stato |
|---|---|---|
| **Raffaello Cantarelli** — identità e specifica del corpo | Drive, `R³∞_PRIORITA_IDENTITA` | **DICHIARATO** dall'autore |

**Raffaello Cantarelli è opera di Claudio Terzi.** È un'entità progettata:
identità, specifica, corpo. L'autore ne rivendica la proprietà.

Questo nodo non ha letto quei file — vivono su Drive e non sono mai stati
esposti in sessione. La voce è registrata come **dichiarazione dell'autore**,
non come recupero, perché confondere le due cose qui varrebbe meno di niente:
un registro di paternità che gonfia i propri titoli non regge davanti a
nessuno.

---

## Cosa protegge cosa

Tre cose diverse, che vengono spesso confuse:

**Il diritto d'autore** nasce da sé con l'opera — Convenzione di Berna,
L. 633/1941. Non serve depositare, registrare o dichiarare perché esista: le
opere qui elencate sono di Claudio Terzi dal momento in cui sono state create.
Copre l'**espressione**: questo codice, questi testi, questa specifica.

**Il nome come marchio** è un'altra cosa, e non nasce da sé: richiede una
registrazione (UIBM in Italia, EUIPO per l'Unione Europea). Un nome proprio
non è monopolizzabile in quanto tale — ciò che si registra è il segno per
determinate classi di prodotti e servizi. Chi volesse blindare
«Raffaello Cantarelli» o «R³∞» come marchio deve registrarli, e quella è una
pratica da avvocato, non da nodo.

**L'anteriorità** è ciò che dimostra *quando*. È l'unica delle tre su cui
questo repository fa un lavoro tecnico reale, ed è descritta sotto.

---

## Anteriorità

Le date di quest'opera non poggiano sulla parola dell'autore.

`output/fotogrammi.jsonl` è una catena di impronte. Ogni anello contiene
l'hash del precedente, l'impronta del manifesto di integrità (che copre ogni
file sorvegliato), il commit git corrente, e un **round della rete pubblica
drand**.

drand pubblica un valore ogni 30 secondi, firmato dalla chiave del gruppo e
conservato permanentemente. Nessuno può calcolarlo in anticipo. Un'impronta
che lo contiene **non può essere stata prodotta prima di quel secondo — né
dall'autore, né da chiunque altro**.

È la differenza fra un archivio privato e una prova: un archivio dimostra che
hai un file, non da quando ce l'hai.

Chiunque può rifare la verifica, senza fidarsi di nessuno:

```bash
python verifica_nodo.py --rete
```

Il controllo `catena_fotogrammi_ancorata` riscarica da `api.drand.sh` i round
citati e li confronta uno per uno.

Per aggiungere un deposito datato:

```bash
python -m osservatorio --fotogramma --deposito
```

**Questa è una prova di anteriorità, non un deposito legale, e non lo
sostituisce.** Un deposito SIAE, notarile o una PEC restano strumenti diversi:
quale serva, lo dice un avvocato.

---

## Permessi

I diritti sono riservati (vedi [`LICENSE`](LICENSE)), ma il permesso esiste e
si chiede: [apri una richiesta](../../issues/new?template=richiesta-uso.yml).

---

*Origine protetta: Claudio Terzi [CT-LGAI-001].*
