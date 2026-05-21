import logging
import os
import re

_PII_PATTERN = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')


def _mask_pii(text: str) -> str:
    def _replace(match: re.Match) -> str:
        value = match.group()
        return value[:3] + "***"
    return _PII_PATTERN.sub(_replace, text)


class _PIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _mask_pii(str(record.msg))
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(_mask_pii(str(a)) for a in record.args)
            else:
                record.args = _mask_pii(str(record.args))
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
