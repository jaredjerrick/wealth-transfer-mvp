"""Wealth-transfer strategy modules.

Each strategy implements the `Strategy` ABC and is wholly responsible for
its own lifecycle math: contribution → accumulation → transfer → recipient
treatment → terminal after-tax value in the recipient's hands.
"""

from .base import Strategy, StrategyResult, YearlyRow
from .taxable_brokerage import TaxableBrokerageStrategy
from .hold_until_death import HoldUntilDeathStrategy
from .section_529 import Section529Strategy
from .ugma_utma import UGMAUTMAStrategy
from .traditional_ira import TraditionalIRAStrategy
from .roth_ira import RothIRAStrategy
from .trump_account import TrumpAccountStrategy


ALL_STRATEGIES = [
    TaxableBrokerageStrategy,
    HoldUntilDeathStrategy,
    Section529Strategy,
    UGMAUTMAStrategy,
    TraditionalIRAStrategy,
    RothIRAStrategy,
    TrumpAccountStrategy,
]


__all__ = [
    "Strategy",
    "StrategyResult",
    "YearlyRow",
    "TaxableBrokerageStrategy",
    "HoldUntilDeathStrategy",
    "Section529Strategy",
    "UGMAUTMAStrategy",
    "TraditionalIRAStrategy",
    "RothIRAStrategy",
    "TrumpAccountStrategy",
    "ALL_STRATEGIES",
]
