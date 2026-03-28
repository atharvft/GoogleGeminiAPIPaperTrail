"""
Residence Certificate — field bounding boxes.

Approximate layout — calibrate when a reference scan is available.
Format: [x1, y1, x2, y2]
"""

REFERENCE_W = 1240
REFERENCE_H = 1754

RESIDENCE_CERTIFICATE_TEMPLATE: dict[str, list[int]] = {
    "full_name":                    [200, 500, 1100, 560],
    "father_husband_name":          [200, 580, 1100, 640],
    "residential_address":          [200, 680, 1100, 790],
    "mobile_number":                [200, 810, 600,  860],
    "purpose_of_certificate":       [200, 900, 1100, 960],
    "duration_of_residence_years":  [200, 980, 500,  1030],
    "date":                         [200, 1200, 550, 1250],
    "place":                        [600, 1200, 1100, 1250],
}
