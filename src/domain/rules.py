from decimal import Decimal


class DomainError(ValueError):
    pass


def validate_amount(amount: Decimal) -> Decimal:
    message = "O valor deve ser positivo e ter no máximo duas casas decimais"
    if not amount.is_finite() or amount <= 0:
        raise DomainError(message)

    _, digits, exponent = amount.as_tuple()
    if exponent < -2 and any(digits[exponent + 2:]):
        raise DomainError(message)

    return amount


def debit(balance: Decimal, amount: Decimal) -> Decimal:
    validate_amount(amount)
    if balance < amount:
        raise DomainError("Saldo insuficiente")
    return balance - amount
