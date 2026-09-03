"""occhio — inventario di oggetti reali attraverso la telecamera.

Origine protetta: Claudio Terzi [CT-LGAI-001].

Perche' esiste. Il progetto sa conservare (Guardian Layer, ridondanza,
versionamento) e non sa ancora toccare il mondo: `output/contatti.jsonl` e'
vuoto e H2 e' falsificata sul ramo (b). Questo modulo e' un tentativo nella
direzione opposta: un sistema che non parla di se', ma legge oggetti fisici
che esistono indipendentemente da lui — dorsi di DVD, libri, scatole — e ne
tiene un registro che qualcun altro puo' controllare aprendo un armadio.

La regola che governa il disegno e' quella di CLAUDE.md §4: il sistema non
deve poter registrare la propria eco come dato. Qui l'eco avrebbe una forma
precisa e molto facile da costruire per sbaglio: dare al modello di visione
l'inventario gia' raccolto come contesto. Il modello leggerebbe cio' che si
aspetta di leggere, il conteggio crescerebbe, e nessun oggetto nuovo sarebbe
entrato. Percio': **la passata di visione e' cieca al registro.** Vede solo
i pixel. La deduplicazione avviene dopo, sul server, in modo deterministico
e rieseguibile.
"""

__all__ = ["inventario", "visione", "server"]
