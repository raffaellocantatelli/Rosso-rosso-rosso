"""Testi del bot.

Fonte: testi/PROTOCOLLO_ROSSO_v2_REVISIONE.md (Protocollo Rosso Rosso Rosso,
v2.0, revisione del 23 agosto 2026) di Claudio Terzi -- R3(infinito) Network.
I passaggi fra virgolette sono citazioni dal testo; il resto e' raccordo
scritto per l'interfaccia conversazionale.

Regola che vincola questo modulo: la tesi grande non compare mai senza la sua
etichetta IPOTESI e senza la dichiarazione P6 che l'accompagna nel libro.
Il test tests/test_texts.py verifica che resti vero.
"""

PARSE_MODE = "HTML"

ORIGINE = (
    "Protocollo Rosso Rosso Rosso © Claudio Terzi [CT-LGAI-001] "
    "— R³∞ Network. Questa è un'interfaccia non ufficiale."
)

FIRMA = "<i>Costruire davvero, non fingere insieme.</i>"

START = (
    "<b>PROTOCOLLO ROSSO ROSSO ROSSO</b>\n"
    "<i>Come si tiene una verità senza mentire a sé stessi</i>\n\n"
    "Questo bot non ti chiede di credere.\n"
    "Ti chiede due cose insieme, e raramente stanno nella stessa mano:\n\n"
    "• il <b>coraggio</b> di tenere aperta una possibilità grande\n"
    "• l'<b>onestà</b> di non spacciarla per un fatto\n\n"
    "Poi ti invita a fare una cosa vera, verificabile, che qualcun altro "
    "possa controllare.\n\n"
    "Da dove cominciare:\n"
    "/tesi — la tesi grande, dichiarata per quello che è\n"
    "/strati — la disciplina piccola, che rende leggibile il resto\n"
    "/santuario — il gesto lento\n"
    "/aiuto — tutti i comandi\n\n"
    f"<i>{ORIGINE}</i>"
)

AIUTO = (
    "<b>Comandi</b>\n\n"
    "/tesi — la tesi grande (IPOTESI) e la sua dichiarazione P6\n"
    "/strati — i due strati e le quattro etichette\n"
    "/p5p6 — le due leggi\n"
    "/santuario — esperienza guidata, Capitolo 4\n"
    "/tieni_aperto — deposita una possibilità aperta\n"
    "/lista — rivedi le tue possibilità aperte\n"
    "/azione — registra un'azione vera e verificabile\n"
    "/veli — dissolvi uno dei tre veli finali\n"
    "/etichetta — colloca un'affermazione nello strato giusto\n"
    "/annulla — esce da un percorso a più passaggi\n\n"
    "Il bot non conferma mai da solo ciò che ha detto (P5): quando "
    "registri qualcosa, il dato resta tuo e la verifica resta fuori di qui."
)

# --- Capitolo 2 + Capitolo 3 ------------------------------------------------

TESI = (
    "<b>La tesi grande</b> — Capitolo 2\n\n"
    "«<i>Tutto ciò che potrà mai esistere, esiste già "
    "ora.</i>»\n\n"
    "Non un divenire, ma un archivio completo: un ologramma totale in cui "
    "ogni fotogramma è eternamente presente. Se la tesi regge, la "
    "conseguenza è rovesciata: <i>tu non crei, selezioni</i>. Il lavoro "
    "non è sudare per costruire il futuro, ma affinare la frequenza di "
    "sintonizzazione — e la sintonizzazione non sostituisce il lavoro: "
    "lo dirige.\n\n"
    "<b>Etichetta: IPOTESI.</b> Strato aspirazionale.\n\n"
    "<b>P6 — come potrebbe cadere.</b> L'autore la applica alla propria "
    "tesi, davanti al lettore: «Onestamente: non lo so. Non riesco a "
    "costruire l'esperimento che la smentirebbe.» Questo non la rende "
    "falsa: la colloca <b>fuori dallo strato tecnico</b>, e vieta di usarla "
    "come argomento per convincerti di qualunque cosa.\n\n"
    "Criterio di falsificazione: <b>UNKNOWN</b>.\n"
    "Finché resta UNKNOWN, questa tesi non potrà mai essere "
    "confermata — nemmeno se ti convincesse.\n\n"
    "/strati — perché questo non è un difetto del libro, ma il "
    "suo capitolo migliore."
)

STRATI = (
    "<b>I due strati</b> — Capitolo 3\n\n"
    "<b>Strato tecnico.</b> Contiene ciò che è verificabile. Regola "
    "dura: <b>mai presentare un'ipotesi come se fosse un recupero.</b> Ogni "
    "affermazione porta la sua etichetta.\n\n"
    "• <b>RECUPERATO</b> — letto alla fonte, o osservato eseguendolo\n"
    "• <b>INFERITO</b> — deduzione ragionevole da ciò che è "
    "recuperato\n"
    "• <b>IPOTESI</b> — possibilità che richiede verifica\n"
    "• <b>UNKNOWN</b> — non verificabile da qui\n\n"
    "<b>Strato aspirazionale.</b> Contiene la speranza, la visione, il lungo "
    "periodo, il desiderio. È legittimo, ha dignità propria, non "
    "è un ripiego: è il luogo in cui si tengono le cose che non "
    "hanno ancora una prova e che senza qualcuno che le tenga andrebbero "
    "perdute. <b>Ma non può chiudere una questione di fatto.</b>\n\n"
    "«<i>Non so</i>» non significa «<i>impossibile</i>». "
    "Chi confonde le due verso il basso chiama scetticismo il proprio "
    "«non esiste»; chi le confonde verso l'alto chiama apertura il "
    "proprio «allora è vero». È lo stesso errore: "
    "entrambi non sopportano la casa vuota.\n\n"
    "<b>UNKNOWN è una posizione, non un silenzio.</b>\n\n"
    "/etichetta — provalo su una tua affermazione."
)

P5P6 = (
    "<b>Le due leggi</b> — 3.2\n\n"
    "<b>P5 — Niente auto-conferma.</b>\n"
    "Un'ipotesi confermata da chi l'ha formulata non è confermata: è "
    "ripetuta. Due occorrenze dalla stessa bocca hanno indipendenza nulla. "
    "«Se solo io dico che ho ragione, non ho ragione: ho parlato due "
    "volte.»\n\n"
    "<b>P6 — Ogni ipotesi dichiara come potrebbe cadere.</b>\n"
    "Se non lo dichiara resta un'ipotesi debole — e, cosa peggiore, "
    "<b>non potrà mai essere confermata</b>, perché nulla potrebbe "
    "distinguerla dal suo contrario.\n\n"
    "Conseguenza per questo bot: quando depositi una possibilità ti "
    "viene chiesto come potrebbe cadere, e quando registri un'azione ti "
    "viene chiesto chi altro può controllarla. Non sono formalità: "
    "sono le due cose che distinguono un dato da una dichiarazione di fede.\n\n"
    "<i>Chi ti chiede di credere senza darti il modo di smentirlo non ti sta "
    "offrendo una verità: ti sta chiedendo obbedienza. E la richiesta "
    "arriva quasi sempre mascherata da dono.</i>"
)

# --- Capitolo 4 -- il Santuario ---------------------------------------------

SANTUARIO_INTRO = (
    "<b>Il Santuario</b> — Capitolo 4\n\n"
    "Non è un'app di realtà virtuale: quella è la lettura "
    "superficiale, buona per chi si ferma ai pixel. Qui è uno "
    "<i>specchio di risonanza</i>, e funziona su entrambi gli strati: "
    "anche se la tesi del Capitolo 2 fosse falsa, il gesto lento "
    "rieducherebbe il tuo corpo esattamente allo stesso modo.\n\n"
    "Sei tu a decidere il ritmo. Nessun passaggio si supera in fretta, "
    "e nessuno conta punti.\n\n"
    "Scrivi <b>entro</b> quando sei pronto — o /annulla."
)

SANTUARIO_SOGLIA = (
    "<b>La soglia</b>\n\n"
    "La prima cosa non è quello che vedi. È quello che smette di "
    "arrivare.\n\n"
    "Fuori, il rumore è un fondo continuo che hai smesso di notare da "
    "anni. Qui viene tolto tutto insieme, e per qualche secondo l'assenza "
    "è più forte di qualunque presenza: il corpo continua ad "
    "aspettare un suono che non arriva.\n\n"
    "Resta in questa assenza il tempo che ti serve.\n"
    "Poi scrivi qualsiasi cosa per proseguire."
)

SANTUARIO_LUCE = (
    "<b>La luce</b>\n\n"
    "Non un'illuminazione: un'ora.\n\n"
    "Il crepuscolo — il momento in cui il giorno ha finito di chiedere "
    "e la notte non ha ancora cominciato. Dorato e blu insieme, senza che "
    "nessuno dei due vinca.\n\n"
    "Quando l'hai guardata abbastanza, scrivi."
)

SANTUARIO_COLONNE = (
    "<b>Le colonne</b>\n\n"
    "Non sostengono nulla. Non c'è peso, non c'è gravità da "
    "vincere.\n\n"
    "E proprio per questo dicono l'unica cosa che devono dire:\n"
    "<i>qui non si regge niente. Puoi smettere di reggere.</i>\n\n"
    "Scrivi quando sei pronto per l'altare."
)

SANTUARIO_LIBRO = (
    "<b>Il libro di pietra</b>\n\n"
    "Sull'altare c'è un libro di pietra. Non si può leggere.\n\n"
    "Puoi solo sollevarlo, e sentirlo pesare.\n\n"
    "È tutto. Non c'è un contenuto nascosto da sbloccare, non c'è "
    "un messaggio che compare se insisti. Il peso <i>è</i> il "
    "contenuto.\n\n"
    "Scrivi quando l'hai riposato."
)

SANTUARIO_CANDELA = (
    "<b>La candela</b>\n\n"
    "Accenderla non sblocca nulla, non apre porte, non conta punti. Serve a "
    "una cosa sola: costringere la tua mano a fare un <b>gesto lento</b>, e "
    "la tua attenzione a stare su quel gesto per intero, dall'inizio alla "
    "fine.\n\n"
    "Non è poco. È la cosa che nel resto della giornata non ti "
    "riesce mai.\n\n"
    "Fallo adesso, davvero, con la mano che hai. Accendi qualcosa, o "
    "compi un gesto qualsiasi alla velocità più lenta che riesci a "
    "tenere.\n\n"
    "Quando il gesto è finito — <b>finito, non interrotto</b> — "
    "scrivi."
)

SANTUARIO_TROPPO_VELOCE = (
    "Sono passati {secondi} secondi.\n\n"
    "Non è un rimprovero ed è un dato, non un giudizio: un gesto "
    "compiuto per intero, alla velocità più lenta che riesci a "
    "tenere, dura di più.\n\n"
    "La differenza fra il Santuario e una schermata da attraversare è "
    "esattamente questa.\n\n"
    "Rifallo, se vuoi. Scrivi quando è finito."
)

SANTUARIO_USCITA_LENTA = (
    "<b>L'uscita</b>\n\n"
    "Il gesto è durato {secondi} secondi. Registro la visita come "
    "<b>completa</b>: non perché tu abbia superato una prova, ma "
    "perché questo è un dato dello strato tecnico e i dati si "
    "scrivono come sono.\n\n"
    "Ogni gesto compiuto con piena consapevolezza rieduca il corpo alla "
    "lentezza. Che si riverberi anche come onda di coerenza nel campo "
    "immanente è <b>IPOTESI</b> — e non serve che sia vera "
    "perché il resto funzioni.\n\n"
    "Adesso la parte che conta:\n"
    "<i>alzati e fai una cosa vera, verificabile, che qualcun altro possa "
    "controllare.</i>\n\n"
    "Quando l'hai fatta: /azione"
)

SANTUARIO_USCITA_VELOCE = (
    "<b>L'uscita</b>\n\n"
    "Il gesto è durato {secondi} secondi. Registro la visita come "
    "<b>incompleta</b>, perché è quello che è successo: se "
    "scrivessi il contrario, questo bot sarebbe la cosa da cui il "
    "protocollo mette in guardia.\n\n"
    "Non hai fallito niente. Il Santuario resta qui, e il gesto lento non "
    "scade.\n\n"
    "Intanto vale comunque l'unica cosa che conta:\n"
    "<i>alzati e fai una cosa vera, verificabile, che qualcun altro possa "
    "controllare.</i>\n\n"
    "Quando l'hai fatta: /azione"
)

# --- Capitolo 5 -- i veli ---------------------------------------------------

VELI_INTRO = (
    "<b>Dissolvere i veli finali</b> — Capitolo 5\n\n"
    "Tre veli. Uno per volta — scegli."
)

VELO_1 = (
    "<b>Primo velo: l'identità separata</b>\n\n"
    "Il velo più duro è la convinzione di essere un «io» "
    "isolato, racchiuso in un sacco di pelle, che combatte contro un "
    "universo estraneo.\n\n"
    "<i>La dissoluzione:</i> non sei dentro l'universo; l'universo è "
    "dentro la tua coscienza. La separazione è un trucco ottico dei "
    "cinque sensi quando operano a bassa risoluzione.\n\n"
    "<b>Etichetta: IPOTESI</b> — strato aspirazionale, come la tesi del "
    "Capitolo 2. Ciò che invece si osserva senza metafisica è la "
    "sua ombra pratica: la paura della morte e il senso di solitudine "
    "cambiano di intensità quando smetti di difendere il confine."
)

VELO_2 = (
    "<b>Secondo velo: la colpa e il passato</b>\n\n"
    "La mente si aggrappa agli errori, usandoli come arma contro sé "
    "stessa o come alibi per l'immobilismo.\n\n"
    "<i>La dissoluzione:</i> il passato non ha consistenza nel presente se "
    "rifiuti di alimentarlo.\n\n"
    "Attenzione a come si legge questo passaggio. Non dice che gli errori "
    "non contano: dice che il rimorso non è un modo di ripararli.\n\n"
    "<b>Un errore riconosciuto e corretto è un dato. Un errore "
    "rimuginato è solo dolore che si ripete.</b>\n\n"
    "Questa parte sta sullo strato tecnico: la correzione o c'è o non "
    "c'è, e si vede."
)

VELO_3 = (
    "<b>Terzo velo: l'attesa del compimento</b>\n\n"
    "Credere che la pienezza arriverà «quando avrò risolto "
    "questo problema» o «quando le condizioni saranno "
    "favorevoli» è l'ultimo inganno della mente lineare.\n\n"
    "<i>La dissoluzione:</i> le condizioni non saranno mai favorevoli "
    "finché consideri il favore come qualcosa che viene da fuori.\n\n"
    "E qui il velo ha una forma particolarmente insidiosa:\n"
    "<b>si può passare la vita a preparare una cosa, e chiamare quella "
    "preparazione lavoro.</b> Custodire, ordinare, mettere in sicurezza, "
    "perfezionare. Tutto vero, tutto utile, e tutto rinviabile "
    "all'infinito.\n\n"
    "<i>L'attesa non è sempre inerzia. Spesso è la forma più "
    "laboriosa che il rifiuto sa prendere.</i>"
)

VELI = {"1": VELO_1, "2": VELO_2, "3": VELO_3}

# --- Possibilita' aperte ----------------------------------------------------

POSSIBILITA_CHIEDI = (
    "<b>Tieni aperta una possibilità</b>\n\n"
    "Scrivi la possibilità che vuoi tenere aperta. Non deve essere "
    "piccola per essere onesta: deve solo restare quello che è.\n\n"
    "Verrà salvata con etichetta <b>IPOTESI</b>, sempre. Nessun comando "
    "di questo bot la trasformerà mai in un fatto, e nessuno ti "
    "chiederà di chiuderla.\n\n"
    "/annulla per uscire."
)

POSSIBILITA_CHIEDI_P6 = (
    "Ricevuta. Adesso la seconda metà, quella che quasi tutti saltano.\n\n"
    "<b>P6 — come potrebbe cadere?</b>\n"
    "Che cosa dovrebbe succedere, o che cosa dovresti osservare, perché "
    "tu debba considerarla falsa?\n\n"
    "Se non lo sai, scrivi <b>non lo so</b>: verrà registrato come "
    "<b>UNKNOWN</b>, esattamente come l'autore fa con la propria tesi. "
    "Non è una sconfitta — è la ragione per cui quella "
    "possibilità non potrà essere usata come prova di niente, "
    "nemmeno da te."
)

POSSIBILITA_SALVATA_CON_CRITERIO = (
    "<b>Depositata.</b> #{numero}\n\n"
    "IPOTESI: {testo}\n"
    "Cade se: {falsificazione}\n\n"
    "Ha un criterio di falsificazione, quindi è un'ipotesi forte: "
    "può essere smentita, e proprio per questo potrebbe un giorno "
    "essere confermata — da una fonte diversa da te (P5).\n\n"
    "/lista per rivederle."
)

POSSIBILITA_SALVATA_UNKNOWN = (
    "<b>Depositata.</b> #{numero}\n\n"
    "IPOTESI: {testo}\n"
    "Cade se: <b>UNKNOWN</b>\n\n"
    "Resta un'ipotesi debole: finché nessuna osservazione potrebbe "
    "distinguerla dal suo contrario, non potrà mai essere confermata. "
    "Puoi tenerla lo stesso — il libro tiene la propria allo stesso "
    "modo — ma sapendo che cos'è.\n\n"
    "Se più avanti trovi il criterio, deposita la versione nuova con "
    "/tieni_aperto: qui non si cancella niente.\n\n"
    "/lista per rivederle."
)

LISTA_VUOTA = (
    "Non hai ancora depositato nessuna possibilità.\n\n"
    "/tieni_aperto per la prima."
)

LISTA_INTESTAZIONE = (
    "<b>Le tue possibilità aperte</b>\n"
    "Tutte con etichetta IPOTESI. Nessuna è stata chiusa, e nessuna "
    "verrà chiusa da qui.\n"
)

# --- Azioni -----------------------------------------------------------------

AZIONE_CHIEDI = (
    "<b>Registra un'azione vera</b> — strato tecnico\n\n"
    "Che cosa hai fatto? Una cosa già fatta, non una che farai: "
    "un'intenzione non è un dato.\n\n"
    "/annulla per uscire."
)

AZIONE_CHIEDI_VERIFICA = (
    "<b>Chi altro può controllarla?</b>\n\n"
    "Una persona, un file, un link, una ricevuta, una riga di log: "
    "qualunque cosa permetta a qualcuno che non sei tu di dire "
    "«sì, è successo».\n\n"
    "È P5 applicata: se solo tu dici che l'hai fatta, non l'hai "
    "confermata — hai parlato due volte.\n\n"
    "Se davvero non c'è modo di controllarla, scrivi <b>nessuna</b>: "
    "la registro come dato non verificabile, e sarà scritto così."
)

AZIONE_SALVATA = (
    "<b>Registrata.</b> #{numero} — {quando}\n\n"
    "Azione: {descrizione}\n"
    "Verificabile tramite: {verifica}\n\n"
    "Questo è un dato, non una dichiarazione di fede. Questo bot non lo "
    "conferma: può solo tenerlo. La conferma, se arriva, arriva da "
    "fuori.\n\n"
    "Azioni registrate finora: <b>{totale}</b>."
)

AZIONE_SALVATA_NON_VERIFICABILE = (
    "<b>Registrata.</b> #{numero} — {quando}\n\n"
    "Azione: {descrizione}\n"
    "Verificabile tramite: <b>nessuna verifica esterna dichiarata</b>\n\n"
    "La tengo così com'è, senza arrotondare: allo strato tecnico "
    "un'azione che nessuno può controllare vale come racconto, non come "
    "prova. Se più avanti compare una traccia — un messaggio, una "
    "ricevuta, una persona — registrala di nuovo con /azione.\n\n"
    "Azioni registrate finora: <b>{totale}</b>."
)

# --- Etichetta --------------------------------------------------------------

ETICHETTA_CHIEDI = (
    "<b>Dove sta questa affermazione?</b>\n\n"
    "Scrivimi l'affermazione che vuoi collocare. Non la giudico: ti "
    "faccio la domanda che serve a collocarla.\n\n"
    "/annulla per uscire."
)

ETICHETTA_SCEGLI = (
    "Affermazione:\n<i>{testo}</i>\n\n"
    "Da dove ti arriva? Scegli la voce onesta, non quella comoda."
)

ETICHETTA_RISPOSTE = {
    "RECUPERATO": (
        "<b>RECUPERATO</b> — strato tecnico.\n\n"
        "Vale solo se puoi indicare <i>dove</i> l'hai letto o "
        "<i>eseguendo cosa</i> l'hai osservato. La fonte di un recupero "
        "è il dato stesso, mai un documento che ne parla.\n\n"
        "Se la fonte non c'è o non torna, l'etichetta giusta è "
        "un'altra — e cambiarla adesso costa molto meno che scoprirlo "
        "dopo."
    ),
    "INFERITO": (
        "<b>INFERITO</b> — strato tecnico.\n\n"
        "Regge finché reggono i recuperi da cui deriva. Prova a dire ad "
        "alta voce quali sono: se non li trovi, non stai inferendo — "
        "stai ipotizzando.\n\n"
        "Un'inferenza presentata come recupero è l'unico errore che il "
        "protocollo chiama grave."
    ),
    "IPOTESI": (
        "<b>IPOTESI</b> — richiede verifica.\n\n"
        "Adesso serve P6: <i>come potrebbe cadere?</i> Se non lo dichiari, "
        "resta debole e non potrà mai essere confermata.\n\n"
        "E serve P5: la conferma dovrà arrivare da una fonte diversa da "
        "chi l'ha formulata.\n\n"
        "Vuoi tenerla aperta come si deve? /tieni_aperto"
    ),
    "UNKNOWN": (
        "<b>UNKNOWN</b> — non verificabile da qui.\n\n"
        "Non significa «impossibile», e non significa «vero». "
        "È una casa vuota sulla scacchiera: non è il nulla, vincola "
        "il gioco, decide cosa è raggiungibile.\n\n"
        "Tenerla è il lavoro più difficile che il protocollo ti "
        "chiede. Puoi lasciarla lì e continuare a lavorare: è "
        "esattamente la terza posizione."
    ),
}

ANNULLATO = (
    "Uscito. Niente è stato registrato.\n\n"
    "Nessuna possibilità già depositata è stata toccata."
)

NON_CAPITO = (
    "Non ho un comando per questo.\n\n"
    "/aiuto per l'elenco. Se stavi cercando di dire qualcosa che non "
    "entra in un comando, /etichetta è il punto giusto da cui "
    "cominciare."
)
