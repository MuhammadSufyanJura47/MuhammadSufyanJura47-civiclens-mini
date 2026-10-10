"""
Three sample complaints for CivicLens Mini.

These are DEMONSTRATION DATA ONLY. Each saved record is flagged
`is_sample=True` and the dashboard labels them accordingly, so demo data is
never mistaken for a real citizen report.

The analyses here are pre-written (not model output) so the demo works even
when no API key is configured. They are intentionally conservative and follow
the same rules the live model is held to: no invented locations or evidence,
priority marked as a suggestion.
"""

from __future__ import annotations

from typing import Any

SAMPLES: list[dict[str, Any]] = [
    {
        "text": (
            "There is a large pothole on Jinnah Avenue near the F-7 Markaz "
            "signal. It has been there for about three weeks and two "
            "motorcycles have already skidded. I have a photo of the damage."
        ),
        "analysis": {
            "category": "Roads & Potholes",
            "summary": "Large pothole near F-7 Markaz signal causing motorcycle skids for ~3 weeks.",
            "reported_duration": "3 weeks",
            "location": "Jinnah Avenue near F-7 Markaz signal",
            "evidence_mentioned": ["photo of the damage"],
            "suggested_priority": "High",
            "priority_reasons": [
                "Multiple skid incidents reported (safety risk).",
                "Persisting for about three weeks without repair.",
            ],
        },
    },
    {
        "text": (
            "Our street in G-9/2 has had no water supply for the last five "
            "days. Several families are affected and we are buying water "
            "tankers at our own cost."
        ),
        "analysis": {
            "category": "Water Supply",
            "summary": "No water supply in G-9/2 for five days; residents buying tankers.",
            "reported_duration": "5 days",
            "location": "G-9/2",
            "evidence_mentioned": [],
            "suggested_priority": "High",
            "priority_reasons": [
                "Essential service outage affecting multiple families.",
                "Ongoing for five days with out-of-pocket cost to residents.",
            ],
        },
    },
    {
        "text": (
            "The street light outside the park has been flickering at night "
            "for a couple of days. It is not urgent but makes the walkway a "
            "bit dark."
        ),
        "analysis": {
            "category": "Street Lighting",
            "summary": "Flickering street light by a park making the walkway dark at night.",
            "reported_duration": "a couple of days",
            "location": None,
            "evidence_mentioned": [],
            "suggested_priority": "Low",
            "priority_reasons": [
                "Minor inconvenience, no safety incident reported.",
                "Short duration and low stated urgency.",
            ],
        },
    },
]
