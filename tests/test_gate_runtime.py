"""Gate cross-platform e selezione automatica del profilo reale."""
import os
import sys

import verificatore
from sdq1.llm.router import Router
from sdq1.llm.providers.ollama_provider import scegli_modello


class ProviderFinto:
    def __init__(self, disponibile):
        self.disponibile = disponibile

    def available(self):
        return self.disponibile


def router_finto(**stato):
    r = Router.__new__(Router)
    r.providers = {
        "anthropic": ProviderFinto(stato.get("anthropic", False)),
        "gemini": ProviderFinto(stato.get("gemini", False)),
        "deepseek": ProviderFinto(stato.get("deepseek", False)),
        "ollama": ProviderFinto(stato.get("ollama", False)),
        "stub": ProviderFinto(True),
    }
    return r


def test_auto_sceglie_locale_se_solo_ollama_e_disponibile():
    r = router_finto(ollama=True)
    assert r.profilo_reale_disponibile() == "locale"


def test_auto_preferisce_default_se_un_provider_default_e_disponibile():
    r = router_finto(gemini=True, ollama=True)
    assert r.profilo_reale_disponibile() == "default"


def test_auto_restituisce_none_se_il_core_e_spento():
    r = router_finto()
    assert r.profilo_reale_disponibile() is None


def test_verificatore_usa_l_interprete_corrente_e_espande_home():
    comando = verificatore._comando_eseguibile(["python3", "~/prova-r3"])
    assert comando[0] == sys.executable
    assert comando[1] == os.path.expanduser("~/prova-r3")


def test_ollama_generico_preferisce_raffaello():
    assert scegli_modello(["qwen3.5:4b", "raffaello-r3:3b"]) == "raffaello-r3:3b"


def test_ollama_non_dichiara_disponibile_un_modello_richiesto_ma_assente():
    assert scegli_modello(["qwen3.5:4b"], "llama3") is None
