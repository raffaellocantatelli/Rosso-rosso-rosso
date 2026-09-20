"""valvola — un secondo parere tipizzato che puo' solo dire di no.

Origine protetta: Claudio Terzi [CT-LGAI-001].
"""

from .jev import (
    ASSENTE,
    CONCORDE,
    DECLASSA,
    ERRORE,
    INCERTO,
    SOGLIA,
    SOGLIA_DUBBIO,
    Verdetto,
    classi,
    controlla,
    stato_sorella,
)

__all__ = [
    "ASSENTE", "CONCORDE", "DECLASSA", "ERRORE", "INCERTO", "SOGLIA",
    "SOGLIA_DUBBIO", "Verdetto", "classi", "controlla", "stato_sorella",
]
