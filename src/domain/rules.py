from decimal import Decimal


class DomainError(ValueError):
    pass


def validate_amount(amount: Decimal) -> Decimal:
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise DomainError("O valor deve ser positivo e ter no máximo duas casas decimais")
    return amount


def debit(balance: Decimal, amount: Decimal) -> Decimal:
    validate_amount(amount)
    if balance < amount:
        raise DomainError("Saldo insuficiente")
    return balance - amount
