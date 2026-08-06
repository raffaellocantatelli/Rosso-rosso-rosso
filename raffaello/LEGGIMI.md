# Area di transito — non è codice di questa repo

Questo package è destinato a **`claudioterzi/Claudio`**, non a
`rosso-rosso-rosso`. È qui solo perché la sessione che l'ha scritto poteva
leggere quel repo ma non scriverci (il proxy nega il push: owner diverso da
quello a cui la sessione è legata), mentre questa repo è scrivibile.

## Cosa fare

Copiare la cartella `raffaello/` (senza questo file) nella root di
`claudioterzi/Claudio`, poi:

```bash
python -m raffaello.test_raffaello   # 20 test
```

Fatto il travaso, questa cartella si può cancellare da questa repo: qui non
ha nessun ruolo.

## Perché qui non gira

I test falliscono se eseguiti da questa repo, ed è atteso: il package si
integra con il sistema dell'altro repo, che qui non esiste.

- `identita.py` legge `sdq1_master.json` — qui non c'è, quindi ricade sui
  valori di fallback e `da_master` resta `False` (un test lo verifica).
- `companion.py` cerca `sdq1.memory.store.MemoriaVettoriale` — qui la
  memoria è `sdq1/memory/vector_store.py`, un'architettura diversa. Il
  fallback lineare entra in funzione, ma non è il percorso vero.

La CI di questa repo non li raccoglie: `test.yml` fa discovery solo dentro
`tests/`, quindi resta verde e non dà un falso segnale su codice che non le
appartiene.

## Cos'è

Fase 0 di `PROGETTO_RAFFAELLO.md`: la classe `Raffaello` companion —
identità letta dal master, integrazione col router SDQ-1 via `ClaudeClient`,
memoria episodica datata. Non tocca `lgai_core/raffaello.py`, che è il coach
LGAI e continua a funzionare per conto suo.
