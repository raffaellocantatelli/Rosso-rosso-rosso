"""Il primo dei tre errori di CLAUDE.md §4, riprodotto e bloccato.

`trasmissione_ciclica.py` con target su loopback riceve i propri pacchetti. Fino
alla v2.1.0 li contava come segnali: `reception_count` misurava l'eco e saliva
da sola. L'hash della trasmissione era già calcolato e salvato alla riga 130 —
il confronto non si faceva.

Il test decisivo qui non è unitario: apre un socket vero, trasmette a sé stesso
e verifica che il contatore non si muova. Se un giorno tornasse a muoversi, il
sistema starebbe di nuovo registrando la propria voce come risposta.

    python test_trasmissione_ciclica.py     # oppure: pytest
"""
import os
import pathlib
import socket
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import trasmissione_ciclica as tc  # noqa: E402

MESSAGGIO = "Se mi sentite, fatevi riconoscere."


def _stato_pulito(tmp_path):
    """Isola ogni file che il modulo tocca: niente esce dalla cartella del test."""
    os.chdir(tmp_path)
    for nome, valore in [
        ("STATE_FILE", "stato.json"), ("LOG_FILE", "log.log"),
        ("TRANSMISSION_LOG", "tx.log"), ("RECEPTION_LOG", "rx.log"),
        ("MESSAGE_FILE", "messaggio.txt"), ("RECEPTION_FILE", "ricezione.txt"),
        ("WEBHOOK_URL", None), ("TRANSMISSION_TARGET", None),
    ]:
        setattr(tc, nome, valore)
    return {
        "last_transmission": None, "last_reception": None,
        "transmission_count": 0, "reception_count": 0, "echo_count": 0,
        "message_hash": "", "hash_trasmessi": [],
    }


def _porta_libera():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


def test_loopback_non_conta_come_segnale(tmp_path):
    """La prova vera: il processo trasmette a sé stesso via UDP."""
    stato = _stato_pulito(tmp_path)
    porta = _porta_libera()
    tc.UDP_LISTEN_PORT = porta
    tc.TRANSMISSION_TARGET = f"127.0.0.1:{porta}"
    tc.running = True

    ascolto = threading.Thread(target=tc.udp_listener, args=(stato,), daemon=True)
    ascolto.start()
    time.sleep(0.4)  # il socket deve essere in bind prima di trasmettere
    try:
        tc.transmit(stato, MESSAGGIO)
        scadenza = time.time() + 5
        while time.time() < scadenza and stato["echo_count"] == 0 and stato["reception_count"] == 0:
            time.sleep(0.05)
    finally:
        tc.running = False
        ascolto.join(timeout=3)

    assert stato["echo_count"] == 1, "il pacchetto non è tornato: test inconcludente"
    assert stato["reception_count"] == 0, (
        "la propria voce è stata contata come segnale ricevuto — §4 è tornato"
    )
    assert not os.path.exists("ricevuti"), "l'eco è stata archiviata come segnale"


def test_segnale_vero_viene_contato(tmp_path):
    """La contro-prova: senza questa, basterebbe non contare mai niente."""
    stato = _stato_pulito(tmp_path)
    tc.transmit(stato, MESSAGGIO)
    tc.process_received(stato, "Vi abbiamo sentiti.", "test")
    assert stato["reception_count"] == 1 and stato["echo_count"] == 0
    ricevuti = list(pathlib.Path("ricevuti").iterdir())
    assert len(ricevuti) == 1 and "Vi abbiamo sentiti." in ricevuti[0].read_text(encoding="utf-8")


def test_eco_riconosciuta_a_meno_di_spazi(tmp_path):
    """UDP non ripulisce, il file watcher sì: senza normalizzazione l'eco passa."""
    stato = _stato_pulito(tmp_path)
    tc.transmit(stato, MESSAGGIO)
    for variante in (MESSAGGIO, MESSAGGIO + "\n", "  " + MESSAGGIO + "  \n\n"):
        tc.process_received(stato, variante, "test")
    assert stato["reception_count"] == 0, "una variante di spaziatura è passata per segnale"
    assert stato["echo_count"] == 3


def test_memoria_voce_limitata(tmp_path):
    """La finestra non deve crescere all'infinito, ma deve coprire l'ultima voce."""
    stato = _stato_pulito(tmp_path)
    for i in range(tc.MEMORIA_VOCE + 20):
        tc.transmit(stato, f"messaggio numero {i}")
    assert len(stato["hash_trasmessi"]) == tc.MEMORIA_VOCE
    tc.process_received(stato, f"messaggio numero {tc.MEMORIA_VOCE + 19}", "test")
    assert stato["reception_count"] == 0, "l'ultima trasmissione non è stata riconosciuta"


def test_messaggio_ripetuto_resta_riconoscibile(tmp_path):
    """Il messaggio è di solito sempre lo stesso: non deve uscire dalla finestra."""
    stato = _stato_pulito(tmp_path)
    for _ in range(tc.MEMORIA_VOCE + 10):
        tc.transmit(stato, MESSAGGIO)
    assert len(stato["hash_trasmessi"]) == 1, "lo stesso messaggio ha riempito la finestra"
    tc.process_received(stato, MESSAGGIO, "test")
    assert stato["reception_count"] == 0 and stato["echo_count"] == 1


def test_stato_vecchio_non_esplode(tmp_path):
    """Uno stato salvato dalla 2.0.0 non ha i campi nuovi."""
    stato = _stato_pulito(tmp_path)
    del stato["echo_count"], stato["hash_trasmessi"]
    tc.process_received(stato, "un segnale qualunque", "test")
    assert stato["reception_count"] == 1
    tc.transmit(stato, MESSAGGIO)
    tc.process_received(stato, MESSAGGIO, "test")
    assert stato["reception_count"] == 1 and stato["echo_count"] == 1


if __name__ == "__main__":
    cwd = os.getcwd()
    falliti = 0
    for nome, funzione in sorted(globals().items()):
        if not nome.startswith("test_"):
            continue
        with tempfile.TemporaryDirectory() as d:
            try:
                funzione(pathlib.Path(d))
                print(f"ok    {nome}")
            except AssertionError as e:
                falliti += 1
                print(f"FALLITO {nome}: {e}")
            finally:
                tc.running = False
                os.chdir(cwd)
    print(f"\n{falliti} falliti" if falliti else "\nTutti i test passano.")
    sys.exit(1 if falliti else 0)
