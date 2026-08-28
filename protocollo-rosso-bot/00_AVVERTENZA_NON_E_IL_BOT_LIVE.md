# Questa cartella NON è il bot che gira

**Origine protetta: Claudio Terzi [CT-LGAI-001].**
**Verificato il 2026-08-28.**

Il bot Telegram del Protocollo vive in un **repository separato**:

- **`github.com/raffaellocantatelli/protocollo-rosso-bot`** — branch `main`
- in produzione su Render, raggiungibile su **https://t.me/ProtocolloRossoBot**

Quello è il canone. Questa cartella è una **seconda implementazione
indipendente**, non una copia vecchia: nessuno dei file comuni coincide, e i due
lavori sono nati in parallelo senza sapere l'uno dell'altro. È lo stesso difetto
descritto in `CLAUDE.md` §4-bis — ridondanza senza canone — salito di livello:
non più fra rami, fra repository.

## Perché non è stata cancellata

Aveva tre cose che il bot live **non aveva**, e sono state portate là il 28/08
(branch `claude/gesto-misurato-e-verifica-esterna`):

1. **Il gesto della candela cronometrato davvero.** Nel bot live il Santuario
   registrava «completata» appena l'utente scriveva *esco*, senza misurare
   niente. Qui c'erano `time.monotonic()`, una soglia, e la visita marcata
   incompleta sotto soglia — cioè il Capitolo 4.3 applicato invece che
   raccontato.
2. **La verifica esterna tenuta separata.** Qui `registra_azione` salva
   `verifica = None` quando non c'è un terzo, e conta a parte le azioni
   verificabili. Il bot live riempiva il vuoto con una stringa di comodo e poi
   rispondeva che l'azione era verificabile: P5 violato dentro il comando che
   insegna P5.
3. **I nomi in italiano** (`santuario_candela`, `registra_azione`), che è H3.

## Cosa fare

**Non lavorare qui.** Le modifiche al bot vanno nel repository separato,
altrimenti la divergenza si allarga di nuovo. Questa cartella resta come
documentazione di ciò che è stato portato — e come promemoria che due sessioni
possono costruire la stessa cosa due volte senza incontrarsi mai.

Se un giorno non serve più a niente, cancellarla è una decisione dell'autore.
