import pytest
from uuid import uuid4
from src.models.signal import Signal


def test_signal_to_dict():
    signal = Signal(
        signal_id=uuid4(),
        symbol="000001",
        side="BUY",
        confidence=0.75,
        rejected=False,
    )
    result = signal.to_dict()
    assert result["symbol"] == "000001"
    assert result["side"] == "BUY"
    assert result["confidence"] == 0.75