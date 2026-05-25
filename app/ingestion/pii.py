import logging
import re

logger = logging.getLogger(__name__)

_FALLBACK_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "<EMAIL_ADDRESS>"),
    (re.compile(r"\b(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b"), "<PHONE_NUMBER>"),
    (re.compile(r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6011\d{12})\b"), "<CREDIT_CARD>"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "<US_SSN>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<IP_ADDRESS>"),
]

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()
    _presidio_ok = True
    logger.info("PII redaction: presidio-analyzer active")
except Exception:
    _presidio_ok = False
    logger.warning("PII redaction: presidio unavailable, using regex fallback (run: python -m spacy download en_core_web_lg)")


def redact(text: str | None) -> str | None:
    """Redact PII from text before storing in inference_logs previews."""
    if not text:
        return text
    if _presidio_ok:
        try:
            results = _analyzer.analyze(text=text, language="en")
            return _anonymizer.anonymize(text=text, analyzer_results=results).text
        except Exception as e:
            logger.warning("presidio redaction failed, falling back to regex: %s", e)
    for pattern, replacement in _FALLBACK_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
