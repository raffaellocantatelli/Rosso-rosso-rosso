#!/usr/bin/env bash
# Candidate A — OmniRoute 3.8.51 + modelVisibilityDenylist, misurato contro 3.8.50.
#
# Origine protetta: Claudio Terzi [CT-LGAI-001].
#
# Che cosa fa, in ordine:
#   1. verifica che il demone Docker risponda (se non risponde, esce: non finge)
#   2. procura l'immagine 3.8.51 — costruendola dal sorgente, perche' su Docker
#      Hub quel tag NON esiste (vedi LETTURA_3851.md, verifica del 21/09/2026)
#   3. avvia un container isolato su una porta sua, senza toccare la baseline
#   4. legge /v1/models PRIMA della modifica            -> models_prima.json
#   5. controlla quali voci della denylist corrispondono davvero a un id del
#      catalogo: una voce che non corrisponde a niente non da' errore, semplice-
#      mente non fa niente, ed e' la trappola principale di questa modifica
#   6. applica modelVisibilityDenylist via PATCH /api/settings -> patch_*.json
#   7. rilegge /v1/models DOPO                           -> models_dopo.json
#   8. chiede una completion con model="auto", prima E dopo -> auto_*.json
#   9. chiede la stessa completion con un modello negato NOMINATO esplicitamente
#      -> explicit_*.json  (upstream dichiara che questo NON viene bloccato:
#         serve a misurare il limite reale della modifica, non a superarlo)
#
# Non decide niente: scrive i fatti in DELTA_DIR e il verdetto lo da'
# `python3 falsificatore_delta.py <DELTA_DIR>`.
#
# Variabili (tutte opzionali tranne dove detto):
#   OMNI_IMAGE      immagine gia' pronta; se vuota, viene costruita dal sorgente
#   OMNI_SRC        checkout di OmniRoute su release/v3.8.51 (default: ./OmniRoute)
#   OMNI_PORT       porta host (default 28151)
#   OMNI_MGMT       credenziale di management per PATCH /api/settings
#                   (token CLI `oma_...` o API key con scope manage). Se il
#                   container e' appena nato e senza password, puo' restare vuota.
#   OMNI_KEY        chiave per le chiamate /v1/* (se richiesta)
#   OMNI_DENY       voci denylist separate da virgola
#   DELTA_DIR       dove finiscono gli artefatti (default ./delta-3851-a)
set -uo pipefail

IMAGE="${OMNI_IMAGE:-}"
SRC="${OMNI_SRC:-./OmniRoute}"
PORT="${OMNI_PORT:-28151}"
MGMT="${OMNI_MGMT:-}"
KEY="${OMNI_KEY:-}"
DENY="${OMNI_DENY:-kilo-gateway/anthropic/claude-opus-5,opencode/big-pickle,oc/big-pickle,felo/felo-chat,felo/felo-search}"
DELTA_DIR="${DELTA_DIR:-./delta-3851-a}"
NAME="omniroute-3851-candidate-a"
BASE="http://127.0.0.1:${PORT}"

mkdir -p "$DELTA_DIR"
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
  docker build -t "$IMAGE" "$SRC" || fail "build fallita"
  printf '%s\n' "$REV" > "$DELTA_DIR/sorgente_rev.txt"
else
  log "uso immagine gia' pronta: $IMAGE"
fi
printf '%s\n' "$IMAGE" > "$DELTA_DIR/immagine.txt"

# --- 3. container isolato ----------------------------------------------------
docker rm -f "$NAME" >/dev/null 2>&1 || true
# Nessun override di porta dentro il container: l'immagine ascolta su 20128
# (Dockerfile: ENV PORT=20128 / EXPOSE 20128). Si rimappa solo fuori.
docker run -d --name "$NAME" -p "${PORT}:20128" "$IMAGE" >/dev/null \
  || fail "avvio container fallito"
trap 'docker logs "$NAME" > "$DELTA_DIR/container.log" 2>&1 || true' EXIT

log "attesa /api/health su $BASE ..."
UP=""
for _ in $(seq 1 60); do
  if curl -fsS -m 3 "$BASE/api/health" -o "$DELTA_DIR/health.json" 2>/dev/null; then UP=1; break; fi
  sleep 2
done
[ -n "$UP" ] || fail "il container non ha risposto entro 120s (vedi $DELTA_DIR/container.log)"
log "in piedi."

auth_v1=(); [ -n "$KEY" ]  && auth_v1=(-H "Authorization: Bearer $KEY")
auth_mg=(); [ -n "$MGMT" ] && auth_mg=(-H "Authorization: Bearer $MGMT")

# --- 4. catalogo PRIMA -------------------------------------------------------
curl -sS "${auth_v1[@]}" -o "$DELTA_DIR/models_prima.json" \
     -w '%{http_code}' "$BASE/v1/models" > "$DELTA_DIR/models_prima.status"
log "catalogo prima: HTTP $(cat "$DELTA_DIR/models_prima.status")"

# --- 4-bis. controllo: la stessa chiamata `auto` PRIMA del PATCH -------------
# Senza questo controllo, un `auto` che fallisce dopo non si distingue da un
# ambiente in cui `auto` non ha mai funzionato (nessun provider configurato).
curl -sS "${auth_v1[@]}" -H 'Content-Type: application/json' \
     -d '{"model":"auto","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
     -o "$DELTA_DIR/auto_prima_risposta.json" \
     -w '{"http":%{http_code},"secondi":%{time_total}}' \
     "$BASE/v1/chat/completions" > "$DELTA_DIR/auto_prima.meta.json"
log "auto prima del PATCH: $(cat "$DELTA_DIR/auto_prima.meta.json")"

# --- 5. le voci corrispondono a qualcosa? ------------------------------------
printf '%s\n' "$DENY" | tr ',' '\n' | sed '/^$/d' > "$DELTA_DIR/denylist.txt"
log "voci denylist: $(wc -l < "$DELTA_DIR/denylist.txt")"

# --- 6. PATCH ----------------------------------------------------------------
DENY_JSON="$(python3 - "$DELTA_DIR/denylist.txt" <<'PY'
import json, sys
print(json.dumps({"modelVisibilityDenylist":
    [r.strip() for r in open(sys.argv[1], encoding="utf-8") if r.strip()]}))
PY
)"
curl -sS -X PATCH "$BASE/api/settings" "${auth_mg[@]}" \
     -H 'Content-Type: application/json' -d "$DENY_JSON" \
     -o "$DELTA_DIR/patch_risposta.json" -w '%{http_code}' \
     > "$DELTA_DIR/patch.status"
log "PATCH /api/settings: HTTP $(cat "$DELTA_DIR/patch.status")"

# Rilettura: il verdetto non si fida della risposta del PATCH, guarda lo stato.
curl -sS "${auth_mg[@]}" -o "$DELTA_DIR/settings_dopo.json" \
     -w '%{http_code}' "$BASE/api/settings" > "$DELTA_DIR/settings_dopo.status"

# --- 7. catalogo DOPO --------------------------------------------------------
curl -sS "${auth_v1[@]}" -o "$DELTA_DIR/models_dopo.json" \
     -w '%{http_code}' "$BASE/v1/models" > "$DELTA_DIR/models_dopo.status"
log "catalogo dopo: HTTP $(cat "$DELTA_DIR/models_dopo.status")"

# --- 8. auto -----------------------------------------------------------------
curl -sS "${auth_v1[@]}" -H 'Content-Type: application/json' \
     -d '{"model":"auto","messages":[{"role":"user","content":"ping"}],"max_tokens":16}' \
     -o "$DELTA_DIR/auto_risposta.json" -D "$DELTA_DIR/auto_headers.txt" \
     -w '{"http":%{http_code},"secondi":%{time_total}}' \
     "$BASE/v1/chat/completions" > "$DELTA_DIR/auto.meta.json"
log "auto: $(cat "$DELTA_DIR/auto.meta.json")"

# --- 9. modello negato, chiesto per nome -------------------------------------
NEGATO="$(head -1 "$DELTA_DIR/denylist.txt")"
python3 - "$NEGATO" > "$DELTA_DIR/explicit_richiesta.json" <<'PY'
import json, sys
print(json.dumps({"model": sys.argv[1],
                  "messages": [{"role": "user", "content": "ping"}],
                  "max_tokens": 16}))
PY
curl -sS "${auth_v1[@]}" -H 'Content-Type: application/json' \
     -d @"$DELTA_DIR/explicit_richiesta.json" \
     -o "$DELTA_DIR/explicit_risposta.json" \
     -w '{"http":%{http_code},"secondi":%{time_total},"modello":"'"$NEGATO"'"}' \
     "$BASE/v1/chat/completions" > "$DELTA_DIR/explicit.meta.json"
log "esplicito ($NEGATO): $(cat "$DELTA_DIR/explicit.meta.json")"

log "artefatti in $DELTA_DIR. Verdetto:"
log "  python3 esperimenti/omniroute/falsificatore_delta.py $DELTA_DIR"
log "Il container resta acceso come '$NAME'. Per spegnerlo: docker rm -f $NAME"
