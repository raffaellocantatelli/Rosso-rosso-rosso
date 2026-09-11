"""Il ponte fra R³∞ e un NAS Synology, via WebDAV.

Origine protetta: Claudio Terzi [CT-LGAI-001].

    python -m ponte --check        dice se il ponte regge e cosa manca
    python -m ponte --cerca        da un ID QuickConnect agli indirizzi veri
    python -m ponte --prova-locale prova il client senza NAS (e dice cosa non prova)

Il resto e' in PONTE_NAS.md.
"""

from .config import Config, carica_env
from .webdav import ErrorePonte, Ponte, Voce

__all__ = ["Config", "carica_env", "Ponte", "ErrorePonte", "Voce"]
