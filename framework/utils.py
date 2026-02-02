"""
Thryx Utility Functions
"""
from decimal import Decimal


def format_usdc(amount: int) -> str:
    """Format USDC amount (6 decimals) to human readable"""
    value = Decimal(amount) / Decimal(10**6)
    return f"${value:,.2f}"


def parse_usdc(amount: float) -> int:
    """Convert human readable USDC to contract format (6 decimals)"""
    return int(Decimal(str(amount)) * Decimal(10**6))


def format_eth(amount: int) -> str:
    """Format ETH amount (18 decimals) to human readable"""
    value = Decimal(amount) / Decimal(10**18)
    return f"{value:.6f} ETH"


def parse_eth(amount: float) -> int:
    """Convert human readable ETH to wei (18 decimals)"""
    return int(Decimal(str(amount)) * Decimal(10**18))


def format_price(price: int, decimals: int = 8) -> str:
    """Format price with given decimals"""
    value = Decimal(price) / Decimal(10**decimals)
    return f"${value:,.2f}"


def short_address(address: str) -> str:
    """Shorten address for display"""
    return f"{address[:6]}...{address[-4:]}"


def calculate_slippage(expected: int, min_out: int) -> float:
    """Calculate slippage percentage"""
    if expected == 0:
        return 0
    return (expected - min_out) / expected * 100
