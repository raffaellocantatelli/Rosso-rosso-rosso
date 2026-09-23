# Il sito: cosa si pubblica, e cosa no

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

## Che cos'è

La console del prodotto, con **dati congelati e inventati** (l'alloggio
`via-esempio-12` della dimostrazione). Si vede com'è fatto il prodotto:
la pianta, il registro, la consegna controfirmata, i tre banchi del mercato.

Nessuna fotografia, nessun oggetto di casa di nessuno, nessuna firma vera.

## Che cosa NON è, e non può essere

**`occhio` non è un sito.** È un programma che legge fotografie e scrive un
registro sul disco di casa di qualcuno. Un sito statico non ha né un disco
né una chiave di visione. Quindi sul sito:

- la telecamera **non** legge niente;
- il registro **non** si scrive: la carta «da decidere» non compare, perché
  il quadro pubblicato dichiara `sola_lettura`;
- i dati sono quelli della dimostrazione e non cambiano finché non si
  rigenera il sito.

Per far girare il prodotto vero servono un disco che resti e una chiave di
visione: è un server, non una pagina. Vercel non è il posto giusto per
quello — lo è per questa vetrina.

## Come si rigenera

Non si tiene a mano: si rigenera. Copiare `console.html` in una seconda
cartella sarebbe una seconda copia dello stesso concetto (`CLAUDE.md` §6
regola 2), e divergerebbe al primo ritocco.

```bash
python3 sito/costruisci.py      # scrive sito/pubblico/
```

## Come si pubblica su Vercel

Non serve nessun connettore: Vercel importa da GitHub.

1. vercel.com → **Add New… → Project** → importa `Rosso-rosso-rosso`
2. **Root Directory**: `sito`
3. Framework Preset: **Other**. Build e output li legge da `vercel.json`
   (`python3 costruisci.py`, cartella `pubblico`).
4. Deploy.

Se il build su Vercel non trova Python, l'alternativa che funziona sempre:
si lancia `python3 sito/costruisci.py` in locale, si committa
`sito/pubblico/`, e su Vercel si toglie il `buildCommand`.
