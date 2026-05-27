import logging
import os
import re

_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
_PHONE_RE = re.compile(r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}')
# Masks known sensitive field values in structured log lines: field=value
_FIELD_RE = re.compile(
    r'((?:property_address|customer_name|customer_phone|full_name)\s*=\s*)([^\n,|]+)',
    re.IGNORECASE,
)


def _mask_pii(text: str) -> str:
    text = _EMAIL_RE.sub(lambda m: m.group()[:3] + "***", text)
    text = _PHONE_RE.sub("***-***-****", text)
    text = _FIELD_RE.sub(lambda m: m.group(1) + "[REDACTED]", text)
    return text


def _safe_mask(value) -> object:
    """Mask PII in strings; leave non-string values (int, float, etc.) unchanged."""
    if isinstance(value, str):
        return _mask_pii(value)
    return value


class _PIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _mask_pii(str(record.msg))
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(_safe_mask(a) for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: _safe_mask(v) for k, v in record.args.items()}
            else:
                record.args = _safe_mask(record.args)
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logger.setLevel(level)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))
        handler.addFilter(_PIIFilter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
