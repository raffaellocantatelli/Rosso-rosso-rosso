# CAP-R3-004 — la patch di Meta, eseguita

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Data: 2026-09-18 (orologio di sistema, §0). Python 3.11.15, pytest.
Metodo: la patch **non è stata letta e commentata**. È stata materializzata riga
per riga in una sandbox e **eseguita**. Ogni riga qui sotto è RECUPERATO
(osservato eseguendo), salvo dove etichettato altrimenti.

Ricostruzione fedele: 11 file estratti, conteggio righe identico a ogni
intestazione `@@` della patch. Suite: **17 test, 17 passati, 0.03s.**

---

## Il punto: la suite è verde e non tocca PostgreSQL

Ho sabotato **tutti e cinque** i metodi del ramo PostgreSQL vero, facendoli
alzare `AssertionError` alla prima riga. Poi ho rieseguito la suite:

```
sabotate 5 occorrenze su 5 metodi
................. [100%]
17 passed in 0.02s
```

**Copertura del ramo PostgreSQL: zero.** Il codice SQL — CAS atomico,
`FOR UPDATE`, l'indice parziale `uniq_active_node`, i rollback — non è mai
stato eseguito da nessun test, e un errore qualunque dentro di esso passerebbe
inosservato. `test_double_rotation_postgres_sim` collauda un dizionario che si
chiama PostgreSQL.

## Perché succede: il costruttore inghiotte il fallimento

`PostgreSQLNodeRegistry.__init__` cattura `except Exception`, mette
`_use_real = False` e prosegue su un `dict` in RAM. Con un DSN inventato:

```
costruttore:  nessuna eccezione
_use_real  :  False
_real_conn :  None
tipo store :  dict
errore inghiottito: No module named 'psycopg'
register() riuscito, scritto in: {('nodo','k1'): {...'status':'ACTIVE'}}
```

E `FabricNode.from_env`, che sceglie PostgreSQL **proprio perché il DSN c'è**:

```
store dichiarato: PostgreSQLNodeRegistry
persiste su db  : False
chiave attiva   : {'node_id':'nodo-produzione', 'key_id':'k1', ...}
```

In produzione, con il database irraggiungibile, il nodo registra le chiavi, dice
OK, e non persiste niente. Nessun log, nessuna eccezione. Al riavvio il registro
è vuoto — **e il registro delle chiavi è la cosa che non può essere vuota.**

Questo è il difetto del §4 spostato dentro l'infrastruttura: il sistema si
conferma da solo perché sta parlando alla propria RAM.

## Due buchi nel modello delle chiavi

**REVOKED non esiste.** `revoke()` fa `DELETE` della riga. Lo stato `REVOKED`
è dichiarato nel `CHECK` del DDL ed è irraggiungibile. Conseguenza eseguita:

```
dopo revoke, list_keys: []
re-register stesso key_id, public_key DIVERSA -> OK
attiva adesso: {'key_id':'k1', 'public_key':'pub-DELL-ATTACCANTE', ...}
REJECT_CONFLICT sollevato? NO
```

Una chiave revocata si ripresenta con lo stesso `key_id` e una public key
diversa, e viene accettata. È esattamente il caso che `REJECT_CONFLICT` esiste
per fermare.

**Una chiave ROTATED torna ACTIVE**, senza nemmeno passare da revoke:

```
dopo rotate k1->k2: k1 ROTATED, k2 ACTIVE
dopo rotate k2->k1: k1 ACTIVE,  k2 ROTATED
k1 e' tornata ACTIVE: True
```

`rotate` sovrascrive il record esistente con uno nuovo `ACTIVE` se la public key
coincide. Una chiave ruotata via — cioè, nel caso che conta, compromessa — si
rimette in servizio con una rotazione all'indietro.

## Il resto, in breve

| Cosa | Osservato |
|---|---|
| `test_provider_ref_opaco` | scrive la env var e poi riasserisce quel valore: **non può fallire**. `FabricNode` non valida il prefisso `provref:`; ho tolto ogni controllo e il test passa lo stesso |
| `test_concurrent.py` | usa `threading`, che è ciò che R3-PEER aveva escluso. Con la RLock dell'in-memory le due rotazioni sono serializzate: il test non misura concorrenza |
| lock | `InMemoryNodeRegistry._lock` → presente. `PostgreSQLNodeRegistry` → **assente**: il suo `_mem` è condiviso senza alcuna protezione |
| `initial_keys` | accettato dal costruttore e mai usato. `test_mutable_default_is_none` verifica il default di un parametro morto |
| `get_active`/`list_keys` (ramo reale) | nessun `commit()`/`rollback()`: lasciano la connessione *idle in transaction*. **INFERITO**, non eseguibile senza un PostgreSQL vero |

**Ritirato.** Avevo dedotto leggendo che `get_stores()` nel decoratore
condividesse gli stessi due store fra tutti i test parametrizzati. Eseguito:
gli `id()` sono diversi, ogni `@parametrize` chiama `get_stores()` per conto
proprio. L'inferenza era sbagliata, l'esecuzione l'ha smentita — è il motivo
per cui questa rassegna esegue invece di leggere.

---

## Cosa decide Claudio

1. **La patch non è pronta.** Non per come è scritta — per cosa dimostra: verde
   su un dizionario, muta su un database assente, con due modi di far tornare
   ACTIVE una chiave che non dovrebbe esserlo.
2. **La correzione minima è una riga:** il costruttore deve **alzare** invece di
   ripiegare. Se il DSN c'è, PostgreSQL è obbligatorio; l'in-memory si sceglie,
   non si eredita da un errore. Tutto il resto viene dopo.
3. **Nessun merge finché la suite non gira contro un PostgreSQL vero** (un
   container in CI). Finché il sabotaggio dei cinque metodi lascia la suite
   verde, quei test non stanno verificando niente.

---

## Non credere a questo file

`rassegna.py` dice la regola: **si chiedono esecuzioni, non pareri.** Un
documento che riporta un'esecuzione è già di secondo grado — è la mia parola su
cosa ho visto. Quindi non fermarti qui:

```bash
python3 verifiche/cap_r3_004/prova.py
```

Ricostruisce gli 11 file da `PATCH_ORIGINALE.diff` — il diff come è arrivato —
in una cartella temporanea, verifica che il conteggio righe coincida con ogni
`@@`, esegue la suite di Meta, sabota i cinque metodi PostgreSQL e riprova, e
poi mette alla prova i sette difetti uno per uno.

- **uscita 0** — i sette difetti ci sono ancora: questo file regge.
- **uscita 1** — almeno uno non si riproduce. La patch è stata corretta, oppure
  mi sbagliavo. In tutti e due i casi questo file è superato e va riscritto su
  quell'esecuzione, non su quella del 18/09.

È il P6 applicato a una rassegna: ho detto come potrei essere smentito, e l'ho
reso un comando.
