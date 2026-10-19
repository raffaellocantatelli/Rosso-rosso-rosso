#!/bin/bash
# ONDA/1.0 — collaudo dello stack Docker: ogni criterio è un passo eseguito, PASS o FAIL.
#
#   ONDA_BASE=/volume1/docker/onda ONDA_CONTROLLO_DIR=<cartella con CONTROLLO-001.key> \
#     bash onda/collaudo_docker.sh
#
# Si lancia dalla radice del repository. ONDA_NO_BUILD=1 usa l'immagine r3-onda:1.0
# già costruita.
#
# ATTENZIONE: il collaudo FERMA, METTE IN PAUSA E RIAVVIA gli agenti ONDA, riavvia
# il container Redis di ONDA e fa `down`/`up` del progetto `onda`. Non tocca altri
# container né dati fuori da ONDA_BASE. Sul NAS va lanciato solo con il consenso
# dell'autore. Alla fine lascia gli agenti ATTIVI.
#
# La chiave CONTROLLO-001 serve per STOP/PAUSA/RIPRENDI. Sul NAS non deve restare:
# copiala in una cartella temporanea, lancia il collaudo, cancella la cartella.

set -u
BASE=${ONDA_BASE:?serve ONDA_BASE}
CTL_DIR=${ONDA_CONTROLLO_DIR:?serve ONDA_CONTROLLO_DIR}
C="docker compose -p onda -f onda/docker-compose.ds223.yml"
FALLITI=0
AGENTI="RAFFA-001 SENTIN-004 MEMO-002"
declare -A SERVIZIO=([RAFFA-001]=raffa [SENTIN-004]=sentin [MEMO-002]=memo)

esito() {  # esito <nome> <0|1> [dettaglio]
  if [ "$2" -eq 0 ]; then echo "PASS  $1 ${3:-}"; else echo "FAIL  $1 ${3:-}"; FALLITI=$((FALLITI+1)); fi
}
ctl() {  # un nodo "PC" con la chiave di controllo, sulla rete interna di ONDA
  docker run --rm --network onda_onda \
    -e ONDA_REDIS_URL=redis://redis:6379/0 -e ONDA_REDIS_PASSWORD_FILE=/run/pw \
    -v "$BASE/redis-password:/run/pw:ro" -v "$CTL_DIR:/run/onda/chiavi:ro" \
    -e ONDA_CHIAVI_DIR=/run/onda/chiavi r3-onda:1.0 "$@" 2>/dev/null
}
oss() { $C run --rm --no-deps -T monitor "$@" 2>/dev/null; }
online() { oss stato | grep -q "\"agente\": \"$1\", \"online\": true"; }
stato_di() { oss stato | grep "\"agente\": \"$1\"" | sed -E 's/.*"stato": "([A-Z_]+)".*/\1/'; }
attendi() {  # attendi <secondi> <comando...>
  local fino=$(( $(date +%s) + $1 )); shift
  until "$@"; do [ "$(date +%s)" -ge "$fino" ] && return 1; sleep 1; done
}
tutti_online() { for i in $AGENTI; do online "$i" || return 1; done; }
nessuno_online() { for i in $AGENTI; do online "$i" && return 1; done; return 0; }
in_pausa() { [ "$(stato_di "$1")" = IN_PAUSA ]; }
offline() { ! online "$1"; }

echo "== preparazione"
for i in $AGENTI; do mkdir -p "$BASE/stato/$i"; done
chown -R 1000:1000 "$BASE/stato" 2>/dev/null || true
if [ "${ONDA_NO_BUILD:-0}" = 1 ]; then $C up -d --no-build >/dev/null 2>&1; else $C up -d --build >/dev/null 2>&1; fi
attendi 60 tutti_online; esito "avvio: tre agenti online" $?

echo "== T1 verifica dal vivo (password, AOF, risposte firmate)"
oss verifica --come MONITOR-001 >/tmp/onda_verifica.out; esito "verifica exit 0" $?
grep -q '"password_obbligatoria", "esito": "VERIFICATO"' /tmp/onda_verifica.out; esito "Redis rifiuta chi non ha password" $?

echo "== T2 Redis non raggiungibile dalla rete"
# `docker compose port` stampa ":0" ed esce 0 anche senza porta: non distingue.
# `docker port` sul container stampa una riga per porta pubblicata, niente se nessuna.
# Ammessa solo una porta legata al loopback del NAS (tunnel SSH, DEPLOY §6).
esposte=$(docker port onda-redis-1 | grep -vE -- '-> 127\.0\.0\.1:' || true)
[ -z "$esposte" ]; esito "nessuna porta pubblicata fuori dal loopback" $? "($(docker port onda-redis-1 | tr '\n' ' '))"

echo "== T3 PAUSA durante down/up"
ctl comando PAUSA SENTIN-004 --come CONTROLLO-001 >/dev/null
attendi 15 in_pausa SENTIN-004; esito "SENTIN-004 IN_PAUSA" $?
$C down >/dev/null 2>&1; $C up -d --no-build >/dev/null 2>&1
attendi 60 online SENTIN-004; esito "SENTIN-004 torna online" $?
in_pausa SENTIN-004; esito "SENTIN-004 resta IN_PAUSA dopo down/up" $?
ctl richiesta SENTIN-004 "x" --come CONTROLLO-001 | grep -q IN_PAUSA; esito "SENTIN-004 rifiuta il lavoro" $?
ctl comando RIPRENDI SENTIN-004 --come CONTROLLO-001 >/dev/null

echo "== T4 riavvio di Redis: riconnessione senza identità duplicate"
prima=$(oss stato | grep RAFFA-001 | grep -oE '"incarnazione": [0-9]+, "pid": [0-9]+, "host": "[^"]+"')
$C restart redis >/dev/null 2>&1
attendi 90 tutti_online; esito "tre agenti di nuovo online" $?
dopo=$(oss stato | grep RAFFA-001 | grep -oE '"incarnazione": [0-9]+, "pid": [0-9]+, "host": "[^"]+"')
[ -n "$prima" ] && [ "$prima" = "$dopo" ]; esito "RAFFA-001 stessa incarnazione/pid/host" $? "($dopo)"
$C logs raffa 2>&1 | grep -q '"evento": "redis_perso"'; esito "la disconnessione è registrata" $?
[ "$($C ps -q raffa | wc -l)" -eq 1 ]; esito "un solo container raffa" $?

echo "== T5 heartbeat: agente non raggiungibile -> OFFLINE entro 30 s"
docker pause onda-memo-1 >/dev/null; t0=$(date +%s)
attendi 45 offline MEMO-002; t=$(( $(date +%s) - t0 ))
[ "$t" -le 31 ] && offline MEMO-002; esito "MEMO-002 OFFLINE" $? "(dopo ${t} s, soglia 30)"
docker unpause onda-memo-1 >/dev/null; attendi 30 online MEMO-002; esito "MEMO-002 torna online" $?

echo "== T6 STOP: nessuno riprende prima di RIPRENDI, nemmeno dopo down/up e perdita di data/"
ctl comando STOP '*' --come CONTROLLO-001 >/dev/null
attendi 20 nessuno_online; esito "STOP a tutti: nessuno online" $?
$C down >/dev/null 2>&1
# I dati Redis veri si spostano da parte, non si cancellano: Redis ripartirà VUOTO.
SALVATI="$BASE/data.collaudo-$$"
mv "$BASE/data" "$SALVATI" && mkdir "$BASE/data" || { echo "impossibile spostare data/: interrotto"; exit 99; }
$C up -d --no-build >/dev/null 2>&1; sleep 40
nessuno_online; esito "dopo down/up con Redis vuoto: nessuno online" $?
for i in $AGENTI; do
  ctl richiesta "$i" "x" --come CONTROLLO-001 --timeout 3 | grep -q nessuno_in_ascolto
  esito "$i non risponde" $?
  $C logs "${SERVIZIO[$i]}" 2>&1 | grep -q fermato_da_comando_persistente
  esito "$i si è fermato dalla copia firmata" $?
done
ctl comando RIPRENDI '*' --come CONTROLLO-001 >/dev/null
attendi 150 tutti_online; esito "dopo RIPRENDI esplicito: tre agenti online" $?
$C down >/dev/null 2>&1
# Si cancella solo la data/ VUOTA creata dal collaudo, e solo se l'originale è al sicuro.
[ -d "$SALVATI" ] && rm -rf "$BASE/data" && mv "$SALVATI" "$BASE/data"
$C up -d --no-build >/dev/null 2>&1; ctl comando RIPRENDI '*' --come CONTROLLO-001 >/dev/null
attendi 150 tutti_online; esito "dati Redis originali rimessi, agenti online" $?

echo "== T7 sicurezza: comandi non autorizzati, segreti nei log"
docker run --rm --network onda_onda -e ONDA_REDIS_URL=redis://redis:6379/0 -e ONDA_REDIS_PASSWORD_FILE=/run/pw \
  -v "$BASE/redis-password:/run/pw:ro" -v "$BASE/chiavi:/run/onda/chiavi:ro" -e ONDA_CHIAVI_DIR=/run/onda/chiavi \
  r3-onda:1.0 comando STOP RAFFA-001 --come MONITOR-001 >/dev/null 2>&1
sleep 2; online RAFFA-001; esito "STOP firmato da un osservatore: ignorato" $?
$C logs raffa 2>&1 | grep -q '"motivo": "non_autorizzato"'; esito "il rifiuto è registrato" $?
LOGS=$($C logs 2>&1)
trovato=0
for f in "$BASE"/chiavi/*.key "$CTL_DIR"/*.key "$BASE/redis-password"; do
  v=$(tr -d '\n' < "$f"); [ -n "$v" ] && grep -qF -- "$v" <<<"$LOGS" && { trovato=1; echo "      compare: $(basename "$f")"; }
done
[ $trovato -eq 0 ]; esito "nessuna chiave privata né password nei log" $?

echo
[ $FALLITI -eq 0 ] && echo "COLLAUDO: tutti i passi PASS" || echo "COLLAUDO: $FALLITI passi FAIL"
exit $FALLITI
