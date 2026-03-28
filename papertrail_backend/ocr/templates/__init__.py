"""
ocr/templates/__init__.py
─────────────────────────
Template registry — exports all coordinate maps and their reference dimensions.

Usage
─────
    from papertrail_backend.ocr.templates import TEMPLATES, get_template

    tmpl = get_template("birth_certificate")
    # tmpl["fields"]  → { field_key: [x1, y1, x2, y2], ... }
    # tmpl["ref_w"]   → reference width  (px)
    # tmpl["ref_h"]   → reference height (px)
"""

from .birth_certificate_template import (
    BIRTH_CERTIFICATE_TEMPLATE,
    REFERENCE_W as BC_REF_W,
    REFERENCE_H as BC_REF_H,
)
from .residence_certificate_template import (
    RESIDENCE_CERTIFICATE_TEMPLATE,
    REFERENCE_W as RC_REF_W,
    REFERENCE_H as RC_REF_H,
)

# ── Central registry ──────────────────────────────────────────────────────────
TEMPLATES: dict = {
    "birth_certificate": {
        "fields": BIRTH_CERTIFICATE_TEMPLATE,
        "ref_w":  BC_REF_W,
        "ref_h":  BC_REF_H,
        "display_name": "Birth Certificate",
    },
    "residence_certificate": {
        "fields": RESIDENCE_CERTIFICATE_TEMPLATE,
        "ref_w":  RC_REF_W,
        "ref_h":  RC_REF_H,
        "display_name": "Residence Certificate",
    },
}


def get_template(form_type: str) -> dict | None:
    """Return template metadata for *form_type*, or None if not registered."""
    return TEMPLATES.get(form_type)


def list_form_types() -> list[str]:
    """Return all registered form type keys."""
    return list(TEMPLATES.keys())


__all__ = [
    "TEMPLATES",
    "BIRTH_CERTIFICATE_TEMPLATE",
    "RESIDENCE_CERTIFICATE_TEMPLATE",
    "get_template",
    "list_form_types",
]
