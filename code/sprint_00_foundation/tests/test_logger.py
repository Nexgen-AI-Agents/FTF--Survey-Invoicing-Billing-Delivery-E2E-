import logging
from core.logger import get_logger, _mask_pii


def test_get_logger_returns_logger():
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)


def test_get_logger_same_instance():
    a = get_logger("test.singleton")
    b = get_logger("test.singleton")
    assert a is b


def test_mask_pii_masks_email():
    result = _mask_pii("Send invoice to john.doe@example.com please")
    assert "joh***" in result
    assert "@example.com" not in result


def test_mask_pii_preserves_non_pii():
    text = "Order 1234 processed successfully"
    assert _mask_pii(text) == text


def test_mask_pii_handles_multiple_emails():
    result = _mask_pii("From: abc@test.com, To: xyz@test.com")
    assert "abc@test.com" not in result
    assert "xyz@test.com" not in result
    assert "abc***" in result
    assert "xyz***" in result


def test_logger_has_one_handler():
    logger = get_logger("test.handler_count")
    assert len(logger.handlers) == 1
