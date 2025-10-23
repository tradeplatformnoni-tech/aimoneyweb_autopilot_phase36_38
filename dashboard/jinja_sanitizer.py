# NEOLIGHT_PHASE4700_JINJA_SANITIZER
import re

def sanitize_template(raw_html: str) -> str:
    # Strip non-printable chars that break Jinja parsing
    return re.sub(r'[^\x09\x0A\x0D\x20-\x7E]', '', raw_html)
