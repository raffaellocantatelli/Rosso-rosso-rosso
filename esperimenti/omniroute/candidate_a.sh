#!/usr/bin/env bash
# Candidate A — OmniRoute 3.8.51 + modelVisibilityDenylist, misurato.
#
# Origine protetta: Claudio Terzi [CT-LGAI-001].
#
# Che cosa fa, in ordine:
#   1. verifica che il demone Docker risponda (se non risponde, esce: non finge)
#   2. procura l'immagine — costruendola dal sorgente se non gliene passi una,
#      perche' su Docker Hub il tag 3.8.51 NON esiste (vedi LETTURA_3851.md)
#   3. avvia un container isolato, su loopback e con una password sua
#   4. fa login e tiene il cookie di sessione: senza, ogni chiamata e' 401
#   5. legge /v1/models PRIMA                            -> models_prima.json
#   6. chiama `auto` PRIMA del PATCH (controllo)         -> auto_prima.meta.json
#   7. applica la denylist UNA VOCE ALLA VOLTA (-> per_voce/) e poi tutta
#      intera, rileggendo ogni volta lo stato e il catalogo. Cosi' l'effetto
#      di ogni voce si misura invece di dedurlo dal nome dell'id
#      (su 3.8.50 il PATCH risponde 200 e butta via la chiave in silenzio:
#       fidarsi del codice di risposta qui e' come non misurare)
#   8. rilegge /v1/models DOPO                           -> models_dopo.json
#   9. richiama `auto`                                   -> auto.meta.json
#  10. chiede un modello negato NOMINANDOLO              -> explicit.meta.json
#      (upstream dichiara che questo NON viene bloccato: serve a misurare il
#       limite reale della modifica, non a superarlo)
#
# Non decide niente: scrive i fatti in DELTA_DIR. Il verdetto lo da'
# `python3 falsificatore_delta.py <DELTA_DIR>`.
#
# Variabili, tutte opzionali:
#   OMNI_IMAGE      immagine pronta; se vuota, viene costruita dal sorgente
#   OMNI_SRC        checkout di OmniRoute su release/v3.8.51 (default ./OmniRoute)
#   OMNI_DOCKERFILE Dockerfile da usare per la build (default Dockerfile)
#   OMNI_PORT       porta host, su 127.0.0.1 (default 28151)
#   OMNI_NAME       nome del container (cambialo per misurare 3.8.50 in parallelo)
#   OMNI_PASSWORD   password di management del container di prova
#   OMNI_KEY        chiave /v1 aggiuntiva, se vuoi misurare anche quella strada
#   OMNI_REQUIRE_API_KEY  default false: qui si misura la denylist, non l'auth
#   OMNI_DENY       voci denylist separate da virgola
#   DELTA_DIR       dove finiscono gli artefatti (default ./delta-3851-a)
set -uo pipefail

IMAGE="${OMNI_IMAGE:-}"
SRC="${OMNI_SRC:-./OmniRoute}"
DOCKERFILE="${OMNI_DOCKERFILE:-Dockerfile}"
PORT="${OMNI_PORT:-28151}"
NAME="${OMNI_NAME:-omniroute-3851-candidate-a}"
PASSWORD="${OMNI_PASSWORD:-R3-candidate-a-2026}"
KEY="${OMNI_KEY:-}"
DENY="${OMNI_DENY:-kilo-gateway/anthropic/claude-opus-5,opencode/big-pickle,oc/big-pickle,felo/felo-chat,felo/felo-search}"
DELTA_DIR="${DELTA_DIR:-./delta-3851-a}"
BASE="http://127.0.0.1:${PORT}"

mkdir -p "$DELTA_DIR"
DELTA_DIR="$(cd "$DELTA_DIR" && pwd)"
COOKIE="$DELTA_DIR/cookie.txt"
log() { printf '[A] %s\n' "$*" >&2; }
fail() { printf '[A] STOP: %s\n' "$*" >&2; exit 2; }

# --- 1. il demone risponde? --------------------------------------------------
docker info >/dev/null 2>&1 || fail "demone Docker irraggiungibile. Niente da misurare."

# --- 2. immagine -------------------------------------------------------------
if [ -z "$IMAGE" ]; then
  [ -d "$SRC/.git" ] || fail "manca il sorgente in $SRC. git clone --branch release/v3.8.51 https://github.com/diegosouzapw/OmniRoute $SRC"
  REV="$(git -C "$SRC" rev-parse HEAD)"
  log "build dal sorgente $SRC @ $REV (il tag 3.8.51 non esiste su Docker Hub)"
  IMAGE="omniroute:3.8.51-local"
  docker build -f "$SRC/$DOCKERFILE" -t "$IMAGE" "$SRC" || fail "build fallita"
  printf '%s\n' "$REV" > "$DELTA_DIR/sorgente_rev.txt"
else
  log "uso immagine gia' pronta: $IMAGE"
fi
printf '%s\n' "$IMAGE" > "$DELTA_DIR/immagine.txt"

# --- 3. container isolato ----------------------------------------------------
docker rm -f "$NAME" >/dev/null 2>&1 || true
# Nessun override di porta DENTRO il container: l'immagine ascolta su 20128
# (Dockerfile: ENV PORT=20128 / EXPOSE 20128). Si rimappa solo fuori, e solo
# su 127.0.0.1: un container di prova non deve essere raggiungibile da fuori.
# REQUIRE_API_KEY: l'immagine pubblicata lo forza a true (#13679). Qui si misura
# la denylist, non l'autenticazione — rimettilo a true se vuoi anche quella.
# INITIAL_PASSWORD: senza, l'immagine parte con la password nota 'CHANGEME' e
# la rifiuta da tutto cio' che non e' loopback vero (dentro il container).
docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:20128" \
  -e "REQUIRE_API_KEY=${OMNI_REQUIRE_API_KEY:-false}" \
  -e "INITIAL_PASSWORD=${PASSWORD}" "$IMAGE" >/dev/null \
  || fail "avvio container fallito"
trap 'docker logs "$NAME" > "$DELTA_DIR/container.log" 2>&1 || true' EXIT

log "attesa /api/health su $BASE ..."
UP=""
for _ in $(seq 1 90); do
  if curl -fsS -m 3 "$BASE/api/health" -o "$DELTA_DIR/health.json" 2>/dev/null; then UP=1; break; fi
  sleep 2
done
[ -n "$UP" ] || fail "il container non ha risposto entro 180s (vedi $DELTA_DIR/container.log)"
log "in piedi."

# --- 4. login: senza cookie ogni chiamata e' 401 -----------------------------
rm -f "$COOKIE"
LOGIN_CODE="$(curl -sS -c "$COOKIE" -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,sys;print(json.dumps({"password":sys.argv[1]}))' "$PASSWORD")" \
  -o "$DELTA_DIR/login.json" -w '%{http_code}')"
printf '%s\n' "$LOGIN_CODE" > "$DELTA_DIR/login.status"
log "login: HTTP $LOGIN_CODE"
[ "$LOGIN_CODE" = "200" ] || fail "login fallito: senza sessione non si misura niente"

auth=(-b "$COOKIE")
[ -n "$KEY" ] && auth+=(-H "Authorization: Bearer $KEY")

# --- 5. catalogo PRIMA -------------------------------------------------------
curl -sS "${auth[@]}" -o "$DELTA_DIR/models_prima.json" \
     -w '%{http_code}' "$BASE/v1/models" > "$DELTA_DIR/models_prima.status"
log "catalogo prima: HTTP $(cat "$DELTA_DIR/models_prima.status")"

# --- 6. controllo: `auto` PRIMA del PATCH ------------------------------------
# Senza questo controllo, un `auto` che fallisce dopo non si distingue da un
# ambiente in cui `auto` non ha mai funzionato (nessun provider configurato).
curl -sS "${auth[@]}" -H 'Content-Type: application/json' \
     -d '{"model":"auto","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
     -o "$DELTA_DIR/auto_prima_risposta.json" \
     -w '{"http":%{http_code},"secondi":%{time_total}}' \
     "$BASE/v1/chat/completions" > "$DELTA_DIR/auto_prima.meta.json"
log "auto prima del PATCH: $(cat "$DELTA_DIR/auto_prima.meta.json")"

# --- 7. denylist -------------------------------------------------------------
printf '%s\n' "$DENY" | tr ',' '\n' | sed '/^$/d' > "$DELTA_DIR/denylist.txt"
log "voci denylist: $(wc -l < "$DELTA_DIR/denylist.txt")"

DENY_JSON="$(python3 - "$DELTA_DIR/denylist.txt" <<'PY'
import json, sys
print(json.dumps({"modelVisibilityDenylist":
    [r.strip() for r in open(sys.argv[1], encoding="utf-8") if r.strip()]}))
PY
)"
# 7-bis. UNA VOCE ALLA VOLTA. Attribuire un id sparito alla voce che l'ha fatto
# sparire, deducendolo dal nome, non si puo': il catalogo espone id come
# `oc/big-pickle` (owned_by opencode) e `no-think/dva/claude-opus-5-max`, mentre
# il predicato upstream lavora sull'id interno del modello, che non e' quello
# stampato. Invece di indovinare la corrispondenza, la si misura: si applica una
# voce sola e si guarda che cosa sparisce davvero.
mkdir -p "$DELTA_DIR/per_voce"
N=0
while IFS= read -r VOCE; do
  [ -n "$VOCE" ] || continue
  N=$((N + 1))
  UNA="$(python3 -c 'import json,sys;print(json.dumps({"modelVisibilityDenylist":[sys.argv[1]]}))' "$VOCE")"
  curl -sS -X PATCH "$BASE/api/settings" "${auth[@]}" \
       -H 'Content-Type: application/json' -d "$UNA" \
       -o "$DELTA_DIR/per_voce/${N}_patch.json" -w '%{http_code}' \
       > "$DELTA_DIR/per_voce/${N}_patch.status"
  curl -sS "${auth[@]}" -o "$DELTA_DIR/per_voce/${N}_models.json" \
       -w '%{http_code}' "$BASE/v1/models" > "$DELTA_DIR/per_voce/${N}_models.status"
  printf '%s\n' "$VOCE" > "$DELTA_DIR/per_voce/${N}_voce.txt"
  log "voce $N ($VOCE): PATCH $(cat "$DELTA_DIR/per_voce/${N}_patch.status") catalogo $(cat "$DELTA_DIR/per_voce/${N}_models.status")"
done < "$DELTA_DIR/denylist.txt"

# 7-ter. e adesso tutte insieme.
curl -sS -X PATCH "$BASE/api/settings" "${auth[@]}" \
     -H 'Content-Type: application/json' -d "$DENY_JSON" \
     -o "$DELTA_DIR/patch_risposta.json" -w '%{http_code}' \
     > "$DELTA_DIR/patch.status"
log "PATCH /api/settings: HTTP $(cat "$DELTA_DIR/patch.status")"

# Rilettura. Su 3.8.50 il PATCH risponde 200 e la chiave sparisce senza un
# errore: il codice di risposta non e' la misura, lo stato riletto lo e'.
curl -sS "${auth[@]}" -o "$DELTA_DIR/settings_dopo.json" \
     -w '%{http_code}' "$BASE/api/settings" > "$DELTA_DIR/settings_dopo.status"

# --- 8. catalogo DOPO --------------------------------------------------------
curl -sS "${auth[@]}" -o "$DELTA_DIR/models_dopo.json" \
     -w '%{http_code}' "$BASE/v1/models" > "$DELTA_DIR/models_dopo.status"
log "catalogo dopo: HTTP $(cat "$DELTA_DIR/models_dopo.status")"

# --- 9. auto -----------------------------------------------------------------
curl -sS "${auth[@]}" -H 'Content-Type: application/json' \
     -d '{"model":"auto","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
     -o "$DELTA_DIR/auto_risposta.json" -D "$DELTA_DIR/auto_headers.txt" \
     -w '{"http":%{http_code},"secondi":%{time_total}}' \
     "$BASE/v1/chat/completions" > "$DELTA_DIR/auto.meta.json"
log "auto: $(cat "$DELTA_DIR/auto.meta.json")"

# --- 10. modello negato, chiesto per nome ------------------------------------
NEGATO="$(head -1 "$DELTA_DIR/denylist.txt")"
python3 - "$NEGATO" > "$DELTA_DIR/explicit_richiesta.json" <<'PY'
import json, sys
print(json.dumps({"model": sys.argv[1],
                  "messages": [{"role": "user", "content": "ping"}],
                  "max_tokens": 16}))
PY
curl -sS "${auth[@]}" -H 'Content-Type: application/json' \
     -d @"$DELTA_DIR/explicit_richiesta.json" \
     -o "$DELTA_DIR/explicit_risposta.json" \
     -w '{"http":%{http_code},"secondi":%{time_total},"modello":"'"$NEGATO"'"}' \
     "$BASE/v1/chat/completions" > "$DELTA_DIR/explicit.meta.json"
log "esplicito ($NEGATO): $(cat "$DELTA_DIR/explicit.meta.json")"

log "artefatti in $DELTA_DIR. Verdetto:"
log "  python3 esperimenti/omniroute/falsificatore_delta.py $DELTA_DIR"
log "Il container resta acceso come '$NAME'. Per spegnerlo: docker rm -f $NAME"
