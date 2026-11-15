from decimal import Decimal
import pytest
from src.domain.rules import DomainError, debit, validate_amount


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1"), Decimal("1.001"), Decimal("NaN")])
def test_invalid_amount(amount):
    with pytest.raises(DomainError):
        validate_amount(amount)


def test_valid_amount():
    assert validate_amount(Decimal("1.20")) == Decimal("1.20")


def test_debit_success():
    assert debit(Decimal("50"), Decimal("20")) == Decimal("30")


def test_debit_insufficient():
    with pytest.raises(DomainError, match="insuficiente"):
        debit(Decimal("5"), Decimal("10"))

@pytest.mark.parametrize("text", ["1.2300", "0.010"])
def test_accept_amount_with_only_trailing_zeroes_after_cents(text):
    amount = Decimal(text)
    assert validate_amount(amount) == amount