# Copyright 2026 Google LLC
# Seed script for PinkSlip-9000 Firestore collection

from google.cloud import firestore

# Explicitly hardcoded project ID to prevent Agent Platform project number mismatch
PROJECT_ID = "qwiklabs-gcp-04-5d12cd732544"

SEEDED_INCIDENTS = [
    {
        "id": "omnicorp-support-2026",
        "company": "OmniCorp Global",
        "region": "North America",
        "headcount": 1850,
        "roles_impacted": ["Tier 1 Support", "Customer Success Reps"],
        "ai_technology": "HyperVoice-9 Agent Swarm",
        "corporate_excuse": "Reallocating biological customer interaction units into non-depreciating GPU inference compute clusters for optimized stakeholder empathy.",
        "cynicism_index": 94,
        "gpus_per_worker": 0.45,
        "date": "2026-02-14",
    },
    {
        "id": "apex-code-2026",
        "company": "Apex Cloud Systems",
        "region": "Europe",
        "headcount": 620,
        "roles_impacted": ["Junior Software Engineers", "QA Testers"],
        "ai_technology": "AutoCode-Pro Synthesizer",
        "corporate_excuse": "Streamlining engineering friction by promoting developers to prompt connoisseurs, naturally reducing redundant human-written keystroke overhead.",
        "cynicism_index": 88,
        "gpus_per_worker": 1.2,
        "date": "2026-03-01",
    },
    {
        "id": "cyberfin-analysts-2026",
        "company": "CyberFin Capital",
        "region": "North America",
        "headcount": 450,
        "roles_impacted": ["Junior Financial Analysts", "Spreadsheet Wranglers"],
        "ai_technology": "QuantumLedger Agent",
        "corporate_excuse": "Transitioning from flawed human gut instincts to pure deterministic algorithmic capital allocation models with zero vacation day entitlement.",
        "cynicism_index": 92,
        "gpus_per_worker": 0.8,
        "date": "2026-03-10",
    },
    {
        "id": "neomedia-copy-2026",
        "company": "NeoMedia Conglomerate",
        "region": "Asia-Pacific",
        "headcount": 310,
        "roles_impacted": ["Content Writers", "SEO Specialists"],
        "ai_technology": "ClickBait-Turbo 4.0",
        "corporate_excuse": "Empowering our storytelling ecosystem through high-density synthetic narrative throughput at unprecedented scale.",
        "cynicism_index": 96,
        "gpus_per_worker": 0.15,
        "date": "2026-03-18",
    },
    {
        "id": "globex-translation-2026",
        "company": "Globex Logistics",
        "region": "Latin America",
        "headcount": 780,
        "roles_impacted": ["Document Translators", "Compliance Checkers"],
        "ai_technology": "PolyGlot-Instant Matrix",
        "corporate_excuse": "Eliminating semantic latency in international customs documentation to maximize supply-chain velocity and reduce unnecessary carbon-based breathing in office premises.",
        "cynicism_index": 90,
        "gpus_per_worker": 0.35,
        "date": "2026-03-22",
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("layoff_incidents")

    print(f"Seeding {len(SEEDED_INCIDENTS)} incidents into 'layoff_incidents'...")
    for item in SEEDED_INCIDENTS:
        doc_id = item["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(item)
        print(f"  ✓ Seeded {doc_id} ({item['company']} - {item['headcount']} employees in {item['region']})")

    print("✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
