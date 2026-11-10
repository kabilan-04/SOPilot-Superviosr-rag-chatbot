"""Known plant documents: display names and which revision is current.

QC-SOP-014 has both Rev 03 and Rev 04 in the folder. Rev 04 says it
supersedes Rev 03 (sampling plan, MTC, quarantine, BH-220 dims).
Answering from the old file would send the floor the wrong sample size.
"""

from typing import Dict

CATALOG: Dict[str, dict] = {
    "MNT-MAN-CNC-02_TX-200_Preventive_Maintenance.pdf": {
        "doc_no": "MNT-MAN-CNC-02",
        "title": "MNT-MAN-CNC-02 Rev 02",
        "status": "current",
    },
    "QC-SOP-014_Rev03_Incoming_Material_Inspection.pdf": {
        "doc_no": "QC-SOP-014",
        "title": "QC-SOP-014 Rev 03",
        "status": "superseded",
        "superseded_by": "QC-SOP-014 Rev 04",
    },
    "QC-SOP-014_Rev04_Incoming_Material_Inspection.pdf": {
        "doc_no": "QC-SOP-014",
        "title": "QC-SOP-014 Rev 04",
        "status": "current",
    },
    "SAF-SOP-003_Lockout_Tagout_Procedure.pdf": {
        "doc_no": "SAF-SOP-003",
        "title": "SAF-SOP-003 Rev 05",
        "status": "current",
    },
}

# Phone-sized chips: questions a supervisor actually types on the floor.
SUGGESTIONS = [
    "Alarm AL-104 on CNC-06. What do I do?",
    "Lot of 200: how many samples?",
    "Who can remove a lock?",
    "BH-220 bore tolerance",
]


def meta_for(filename: str) -> dict:
    return CATALOG.get(
        filename,
        {"doc_no": filename, "title": filename, "status": "current"},
    )


def query_wants_old_revision(query: str) -> bool:
    q = query.lower()
    return any(
        phrase in q
        for phrase in (
            "rev 03",
            "rev03",
            "revision 3",
            "old version",
            "old sop",
            "superseded",
            "previous revision",
        )
    )
