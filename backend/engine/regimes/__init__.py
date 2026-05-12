"""State tax regimes — NY, IL, TX.

Each regime implements the `StateRegime` ABC and is the single owner of all
state-specific numbers. The federal calculation engine is regime-agnostic and
calls into these objects via interface methods.
"""

from .base import StateRegime, StateEstateResult
from .ny import NYRegime
from .il import ILRegime
from .tx import TXRegime
from ..inputs import StateCode


def regime_for(state: StateCode, rules: dict) -> StateRegime:
    if state == StateCode.NY:
        return NYRegime(rules)
    if state == StateCode.IL:
        return ILRegime(rules)
    if state == StateCode.TX:
        return TXRegime(rules)
    raise ValueError(f"Unknown state: {state}")


__all__ = ["StateRegime", "StateEstateResult", "NYRegime", "ILRegime", "TXRegime", "regime_for"]
