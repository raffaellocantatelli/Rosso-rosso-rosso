# BUG-R3-H5-EXITCODE-01 — consolidamento

**Stato:** protezione runtime già presente; rettifica dei metadati candidata all'integrazione

**Data del consolidamento:** 2026-09-19

**Base verificata:** `c95f15456bad09e88c3c9b10e5b19d5bcf3c6801`

**Origine:** Claudio Terzi [CT-LGAI-001] — R³∞ Network

## Fatto osservato

La riga H5 del 2026-08-26 in `output/verifiche.jsonl` contiene insieme:

- `exit_code: 1`;
- `esito: regge`;
- transizione `APERTA -> RETTA`;
- un traceback Python causato da un errore 429 del provider.

Nel contratto storico dei falsificatori, `1` significa `REGGE`; Python usa
anche `1` come codice predefinito per un'eccezione non gestita. Il verificatore
ha quindi trasformato «la verifica è andata in crash» in «l'ipotesi regge».

La riga storica resta immutata: è la prova primaria del difetto e non deve
essere riscritta retroattivamente.

## Correzione già presente nel codice

Il commit `3c481b6fd928eaf2b842afcca7a0c12056250c98` aveva già introdotto:

1. `falsificatori.main_protetto()`: un'eccezione diventa `NON_CONCLUSA` (2);
2. difesa nel verificatore: un traceback non può produrre `regge`;
3. ritorno dello stato H5 da `RETTA` ad `APERTA`;
4. test di regressione sul crash;
5. oscuramento delle credenziali nei messaggi d'errore.

## Contraddizione residua trovata il 2026-09-19

Lo stato H5 era `APERTA`, ma `registro_ipotesi.json` conservava ancora:

- `eseguite: 1`;
- `ultimo_esito: regge`.

Questi campi descrivevano come valida la stessa esecuzione che il codice e
l'osservazione `OSS-0003` avevano invalidato.

## Riconciliazione applicata

Senza cancellare o alterare il log storico:

- H5 resta `APERTA`;
- `eseguite` diventa `0`;
- `cadute` resta `0`;
- `ultima` conserva la data del tentativo, per tracciabilità;
- `ultimo_esito` diventa `verifica_fallita`.

Il test sul traceback ora verifica anche che un crash non incrementi il
contatore `eseguite` e che il metadato `ultimo_esito` resti
`verifica_fallita`.

## Regola verificata per questo incidente

```text
TRACEBACK RILEVATO / ECCEZIONE INTERCETTATA / TIMEOUT / EXIT NON_CONCLUSA
    -> verifica_fallita
    -> nessuna transizione di stato
    -> nessun incremento di verifiche.eseguite
    -> conservazione append-only dell'evidenza originale
```

## Limite residuo

La difesa secondaria riconosce esplicitamente il traceback Python. La difesa
primaria resta `main_protetto()` per i falsificatori Python. Un futuro
falsificatore scritto in un altro runtime dovrà convertire ogni errore tecnico
in `NON_CONCLUSA` e avere un test di contratto dedicato prima di essere
registrato.

Non è una prova che qualunque output incompleto venga riconosciuto: il
contratto attuale non ha un marcatore strutturato di completamento.

## Provenienza e rettifica append-only

`registro_osservazioni.jsonl` conserva `OSS-0003` e riceve un nuovo evento
`OSS-0004` che documenta la rettifica dei contatori. Il registro dei nodi
riceve una dichiarazione separata del lavoro. Non è una nuova verifica di H5:
nessun modello viene interrogato e la data dell'ultimo tentativo resta quella
del 26 agosto.

- File sorgente: `output/verifiche.jsonl`, riga 13 sulla base indicata.
- SHA-256 del file: `c26cac41a5deedb9d90b91e95649a9cf70fc362f092d4558c2a28c154048c2b2`.
- SHA-256 della riga originale, incluso il terminatore LF:
  `e14b60c7e55eb16b3124cf5f5d591e6d4baab5f713b024394b0e73ef412d9752`.
- Il campo storico `output_sha256` è troncato a 16 caratteri e si riferisce
  all'output completo allora acquisito; il log conserva solo i primi 800
  caratteri. Non è stato presentato come hash completo ricalcolabile.

## Integrità: perimetro esplicito

Sulla base `c95f154...` il manifesto ha già 118 file fuori elenco e una voce
divergente (`memoria/R3_WORK_QUEUE.yaml`). Questa rettifica aggiorna soltanto
gli hash dei file modificati gia sorvegliati e aggiunge il dossier.
Il registro dei nodi resta fuori dal perimetro del verificatore esistente;
la sua aggiunta append-only e comunque versionata nel medesimo commit.
Il manifesto globale non viene dichiarato conforme: le divergenze precedenti
restano visibili e non vengono assorbite da una rigenerazione indiscriminata.

La PR #7 riguarda già la copertura generale del manifesto e altri interventi.
Non viene modificata né unita qui. Se viene integrata prima di questa patch,
occorre preservare le sue esecuzioni più recenti: sottrarre solo il conteggio
del crash storico, senza riportare `ultima` o `ultimo_esito` al 26 agosto.

## Verifica della prima preparazione (prima di questo commit)

- regressione mirata `TestCrashNonEUnSi`: 2/2 superati;
- suite Core selezionata: 312 test + 3 subtest superati;
- suite `protocollo-rosso-bot`: 30/30 superati;
- nessun test ha richiesto una chiamata reale a un provider;
- si trattava di modifiche locali, non ancora integrate sul ramo di default.

## Verifica della finalizzazione

Eseguito in un ambiente Python 3.12 temporaneo con le dipendenze del progetto:

```bash
python -m pytest -q tests/test_verificatore.py test_registro_ipotesi.py test_registro_osservazioni.py test_latenza.py test_trasmissione_ciclica.py
```

Esito: **60 passed, 3 subtests passed**. Comprende il replay offline della
riga H5 originale. L'accettazione sui dati della base individua ancora una
verifica valida erroneamente conteggiata; sui dati rettificati il numero e 0.
I test misurano il comportamento del verificatore, non il merito di H5.
