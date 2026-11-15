from decimal import Decimal


class DomainError(ValueError):
    pass


def has_fractional_cent(amount: Decimal) -> bool:
    _, digits, exponent = amount.as_tuple()
    return exponent < -2 and any(digits[exponent + 2:])


def validate_amount(amount: Decimal) -> Decimal:
    if not amount.is_finite() or amount <= 0 or has_fractional_cent(amount):
        raise DomainError("O valor deve ser positivo e ter no máximo duas casas decimais")
    return amount


def debit(balance: Decimal, amount: Decimal) -> Decimal:
    validate_amount(amount)
    if balance < amount:
        raise DomainError("Saldo insuficiente")
    return balance - amount
