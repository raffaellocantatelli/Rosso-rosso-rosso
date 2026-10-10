"""Provref opaco: il nodo vede solo `provref:...`, mai l'account raw."""

from __future__ import annotations

import os
from typing import Optional

PROVREF_PREFIX = "provref:"
ENV_PROVIDER_ACCOUNT_REF = "PROVIDER_ACCOUNT_REF"


class OpaqueProvrefError(ValueError):
    pass


def parse_provref(value: Optional[str], *, required: bool = False) -> Optional[str]:
    if value is None or value.strip() == "":
        if required:
            raise OpaqueProvrefError(
                f"{ENV_PROVIDER_ACCOUNT_REF} mancante; atteso {PROVREF_PREFIX}<opaque-id>"
            )
        return None
    ref = value.strip()
    if not ref.startswith(PROVREF_PREFIX):
        raise OpaqueProvrefError(
            f"{ENV_PROVIDER_ACCOUNT_REF} deve essere opaco ({PROVREF_PREFIX}...), "
            "non un account raw"
        )
    opaque = ref[len(PROVREF_PREFIX) :]
    if not opaque or "@" in opaque or opaque.startswith("acct:"):
        raise OpaqueProvrefError("provref opaco invalido: mapping raw vietato sul nodo")
    return ref


def provider_account_ref_from_env(*, required: bool = False) -> Optional[str]:
    return parse_provref(os.getenv(ENV_PROVIDER_ACCOUNT_REF), required=required)
