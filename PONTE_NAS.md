# Il ponte verso il NAS — cosa decide Claudio, cosa fa il codice

**Origine protetta: Claudio Terzi [CT-LGAI-001].**

Scritto l'11/09/2026. Risponde a una cosa sola: *il QuickConnect ID non è un
URL WebDAV, quindi da dove si collega il motore?*

---

## In tre righe

1. **L'indirizzo esterno non devi cercarlo tu.** Il coordinatore Synology lo
   dice, partendo dall'ID QuickConnect: `python -m ponte --cerca <ID> --prova`.
2. **Sul NAS restano tre cose da fare a mano** — nessuna macchina può farle al
   posto tuo: pacchetto WebDAV, account dedicato, cartella. Sono qui sotto.
3. **La password scritta in chat va cambiata comunque**, e il ponte non la
   vuole: legge solo `~/.r3/webdav.env`, che sta fuori da questo repository
   perché questo repository è pubblico.

---

## 1. Perché QuickConnect da solo non basta — RECUPERATO

QuickConnect è un servizio di raggiungibilità: registra il NAS presso un
coordinatore Synology e ne inoltra i servizi DSM. WebDAV è un altro servizio,
che parla HTTP su una porta sua (5005 in chiaro, **5006 in HTTPS**). Un client
WebDAV vuole un URL: `https://qualcosa:5006`. L'ID non lo è.

Quello che si può recuperare dall'ID, però, è *dove* sta il NAS. Verificato
l'11/09 con un ID inesistente, per non usare quello vero in una prova:

```
POST https://global.quickconnect.to/Serv.php
{"version":1,"command":"get_server_info","stop_when_error":false,
 "stop_when_success":false,"id":"dsm_portal_https","serverID":"..."}

→ {"command":"get_server_info","errno":4,"suberrno":1,
   "errinfo":"get_server_info.go:92[Alias not found]","version":1}
```

Il coordinatore risponde a chiunque, senza credenziali: l'ID è un nome
pubblico, non un segreto. Con l'ID vero la risposta contiene DDNS, dominio,
IP pubblico e indirizzi interni. È quello che fa `--cerca`.

**IPOTESI, dichiarata prima di provare (P6):** il tunnel `*.quickconnect.to`
inoltra i servizi DSM registrati con lui, e WebDAV sulla 5006 in generale non è
fra quelli. Se l'unico indirizzo che risponde è il relay, serve comunque il
DDNS o la porta aperta sul router. Si falsifica in un comando: `--cerca --prova`
dice quale indirizzo ha la 5006 aperta.

---

## 2. Le tre cose da fare sul NAS

**a. Attiva WebDAV in HTTPS.** DSM → Centro pacchetti → installa *WebDAV
Server* → Impostazioni → spunta **HTTPS**, porta **5006**. Lascia l'HTTP
(5005) spento: senza HTTPS, utente e password viaggiano in chiaro.

**b. Crea un account solo per R³∞.** DSM → Pannello di controllo → Utenti →
nuovo utente (per esempio `r3`), con:
- accesso **solo** alla cartella condivisa `R3` (lettura/scrittura), niente
  altro;
- niente permessi di amministratore;
- nella scheda Applicazioni: WebDAV **permesso**, il resto negato.

Non è formalità. Il ponte rifiuta da solo di scrivere fuori dalla radice, ma
quel rifiuto è codice mio: l'account con accesso alla sola `R3` è la difesa
che resta se il codice sbaglia.

**c. Cambia la password dell'account che hai scritto in chat.** Una password
detta a un modello è una password pubblicata. Se era quella
dell'amministratore, cambiala e usa il nuovo account `r3` per il ponte.

**Da fuori casa serve anche una via d'ingresso**: o Synology DDNS (Pannello di
controllo → Accesso esterno → DDNS, ti dà un `qualcosa.synology.me`), o la
porta 5006 inoltrata sul router. `--cerca --prova` dice se c'è già.

---

## 3. Le due righe da scrivere, e dove

Fuori dal repository, che è pubblico:

```bash
mkdir -p ~/.r3 && chmod 700 ~/.r3
cat > ~/.r3/webdav.env <<'FINE'
R3_WEBDAV_URL=https://TUO-INDIRIZZO:5006
R3_WEBDAV_UTENTE=r3
R3_WEBDAV_PASSWORD=la-password-del-nuovo-account
R3_WEBDAV_RADICE=/R3
R3_NAS_QUICKCONNECT=il-tuo-id
FINE
chmod 600 ~/.r3/webdav.env
```

Poi:

```bash
python -m ponte --check        # dice se regge, e se non regge dice cosa guardare
```

Su un NAS domestico il certificato è spesso autofirmato e la verifica TLS
fallisce. La cura giusta è esportare il certificato dal NAS e indicare
`R3_WEBDAV_CA=/percorso/cert.pem`. `R3_WEBDAV_INSICURO=1` salta la verifica:
funziona, protegge dall'errore ma non da qualcuno in mezzo, e il ponte lo
stampa ogni volta invece di lasciarlo dimenticare.

---

## 4. Cosa sa fare, una volta aperto

```bash
python -m ponte --elenca                      # cosa c'è nella cartella R3
python -m ponte --deposita stato.json         # manda un file
python -m ponte --preleva stato.json --in qui.json
python -m ponte --deposita-backup             # snapshot sdq1 → NAS
```

`--deposita-backup` è il motivo pratico per cui il ponte esiste adesso:
`sdq1 --backup` scrive in `output/backups/`, che è fuori da git di proposito
(sono registri, e questo repository è pubblico). Su una macchina effimera
quello snapshot muore con la macchina. Il NAS è il primo posto dove può
restare senza essere pubblicato.

---

## 5. Cosa questo lavoro NON dimostra

`python -m ponte --prova-locale` fa girare il client contro un NAS finto in
memoria e passa. **Non prova niente sul tuo NAS**: non che esista, non che la
porta sia aperta, non che l'account abbia i permessi. È la trappola di
`CLAUDE.md` §4 — il sistema che si interroga da solo e registra l'eco come
risposta — e per questo ogni comando che usa il banco finto lo stampa.

L'ipotesi **H12** sorveglia proprio questo: *il ponte non dichiara mai un
esito che non ha ottenuto.* Quattro modi di non avere un NAS, quattro
fallimenti dichiarati:

```bash
python3 falsificatori/h12_ponte_non_finge.py    # esce 1 = REGGE
```

Lo stato del ponte verso il NAS di Claudio, da qui, è **UNKNOWN**. Diventa
RECUPERATO nel momento in cui `--check` gira sulla sua macchina con
l'indirizzo vero, e non un minuto prima.
