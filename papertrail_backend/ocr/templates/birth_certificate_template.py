"""
Birth Certificate — field bounding boxes.

Measured on the reference scan at 1272 × 1600 px
(Government of West Bengal, Department of Health & Family Welfare).

Format: [x1, y1, x2, y2]  (left, top, right, bottom)

Each box covers ONLY the handwritten value area —
not the printed label.  Add padding generously so
slightly mis-aligned scans still capture the ink.
"""

# ── canonical reference size ──────────────────────────────────
REFERENCE_W = 1272
REFERENCE_H = 1600

# ── field regions ─────────────────────────────────────────────
# Row structure (approximate y bands):
#   Name / Sex row        ≈ y 755–810
#   Date of Birth / Place  ≈ y 820–870
#   Mother Name           ≈ y 890–940
#   Father Name           ≈ y 960–1010
#   Address at Birth      ≈ y 1055–1150
#   Permanent Address     ≈ y 1150–1250
#   Registration No       ≈ y 1270–1320
#   Date of Registration  ≈ y 1270–1320
#   Date of Issue         ≈ y 1370–1420

BIRTH_CERTIFICATE_TEMPLATE: dict[str, list[int]] = {
    # ── Name: after "Name:" label, before "Sex:" (left ~75% of width)
    "name":                         [130, 755, 820, 815],

    # ── Sex: right side of name row
    "sex":                          [865, 755, 1220, 815],

    # ── Date of Birth: left half of row 2
    "date_of_birth":                [130, 820, 680, 875],

    # ── Place of Birth: right half of row 2
    "place_of_birth":               [680, 820, 1220, 875],

    # ── Mother's Name: full-width row
    "name_of_mother":               [130, 890, 1220, 950],

    # ── Father's Name: full-width row
    "name_of_father":               [130, 960, 1220, 1020],

    # ── Address at Birth: two-line area
    "address_of_parents_at_birth":  [130, 1060, 1220, 1160],

    # ── Permanent Address: two-line area
    "permanent_address_of_parents": [130, 1165, 1220, 1270],

    # ── Registration No: left half
    "registration_number":          [130, 1275, 630, 1335],

    # ── Date of Registration: right half
    "date_of_registration":         [720, 1275, 1220, 1335],

    # ── Date of Issue: left half of last row
    "date_of_issue":                [130, 1375, 700, 1430],
}
