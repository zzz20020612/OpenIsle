#!/usr/bin/env python3
"""
加载示例数据到数据库

从现有数据库提取有限示例数据，清洗后写入 demo 数据库。
仅包含公开可用的元数据，不包含敏感信息。
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[1]
SQLITE_PATH = os.getenv("SQLITE_PATH", str(ROOT_DIR / "db" / "literature.db"))

DEMO_PAPERS = [
    {
        "doi": "10.1234/livestock-2024",
        "title": "Sustainable Livestock Grazing Systems in Alpine Pastures",
        "journal": "Agriculture Ecosystems & Environment",
        "journal_tier": "other",
        "published_date": "2024-03-15",
        "abstract": "This study examines the impact of rotational grazing on alpine pasture ecosystems. We found that livestock grazing patterns significantly affect biodiversity and soil carbon sequestration.",
        "citation_count": 5,
        "source": "crossref",
        "author": json.dumps([
            {"given": "Maria", "family": "Rossi"},
            {"given": "Hans", "family": "Mueller"},
            {"given": "Jean", "family": "Dupont"}
        ]),
        "keywords": json.dumps(["livestock", "grazing", "alpine pasture", "biodiversity", "soil carbon"]),
        "article_type": "Journal Article",
        "language": "en",
        "volume": "356",
        "issue": "1",
        "page": "45-58",
        "issn": "0167-8809",
        "publisher": "Elsevier",
        "subject": json.dumps(["Ecology", "Agriculture"]),
        "oa_url": "",
        "oa_category": "closed",
        "references_count": 42,
        "external_ids": json.dumps({"crossref": "10.1234/livestock-2024"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
    {
        "doi": "10.7890/grazing-impact-2020",
        "title": "Long-term Effects of Continuous vs Rotational Grazing on Grassland Productivity",
        "journal": "The Rangeland Journal",
        "journal_tier": "other",
        "published_date": "2020-07-01",
        "abstract": "A 10-year field experiment comparing continuous and rotational grazing systems in Australian rangelands. Rotational grazing maintained higher productivity and biodiversity.",
        "citation_count": 18,
        "source": "openalex",
        "author": json.dumps([
            {"given": "James", "family": "Smith"},
            {"given": "Sarah", "family": "Williams"}
        ]),
        "keywords": json.dumps(["rotational grazing", "grassland", "productivity", "rangeland", "Australia"]),
        "article_type": "Journal Article",
        "language": "en",
        "volume": "42",
        "issue": "3",
        "page": "210-225",
        "issn": "1036-9872",
        "publisher": "CSIRO Publishing",
        "subject": json.dumps(["Ecology", "Environmental Science"]),
        "oa_url": "",
        "oa_category": "closed",
        "references_count": 35,
        "external_ids": json.dumps({"openalex": "W1234567890"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
    {
        "doi": "10.3456/sheep-health-2021",
        "title": "Health Monitoring Systems for Sheep Flocks Using Wearable Sensors",
        "journal": "Preventive Veterinary Medicine",
        "journal_tier": "other",
        "published_date": "2021-05-10",
        "abstract": "Wearable sensors for sheep health monitoring show promising results in early disease detection. This study evaluates accelerometer-based activity tracking for detecting lameness in sheep.",
        "citation_count": 28,
        "source": "crossref",
        "author": json.dumps([
            {"given": "Anna", "family": "Taylor"},
            {"given": "David", "family": "Brown"},
            {"given": "Emma", "family": "Wilson"}
        ]),
        "keywords": json.dumps(["sheep", "wearable sensors", "health monitoring", "lameness detection", "precision livestock farming"]),
        "article_type": "Journal Article",
        "language": "en",
        "volume": "198",
        "issue": "1",
        "page": "105-112",
        "issn": "0167-5877",
        "publisher": "Elsevier",
        "subject": json.dumps(["Veterinary Science", "Animal Science"]),
        "oa_url": "https://doi.org/10.3456/sheep-health-2021",
        "oa_category": "hybrid",
        "references_count": 52,
        "external_ids": json.dumps({"crossref": "10.3456/sheep-health-2021"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
    {
        "doi": "10.6789/dairy-robot-2023",
        "title": "Automated Milking Systems in Dairy Cattle: A Review",
        "journal": "Journal of Dairy Science",
        "journal_tier": "other",
        "published_date": "2023-12-20",
        "abstract": "This review summarizes advances in automated milking systems (AMS) for dairy cattle, including robotic milking technology and integration with herd management software.",
        "citation_count": 7,
        "source": "openalex",
        "author": json.dumps([
            {"given": "Thomas", "family": "Johnson"},
            {"given": "Lisa", "family": "Anderson"}
        ]),
        "keywords": json.dumps(["dairy cattle", "automated milking", "robotics", "precision livestock farming", "review"]),
        "article_type": "Journal Review",
        "language": "en",
        "volume": "106",
        "issue": "12",
        "page": "8234-8250",
        "issn": "0022-0302",
        "publisher": "Elsevier",
        "subject": json.dumps(["Animal Science", "Dairy Science"]),
        "oa_url": "https://doi.org/10.6789/dairy-robot-2023",
        "oa_category": "gold",
        "references_count": 89,
        "external_ids": json.dumps({"openalex": "W0987654321"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
    {
        "doi": "10.1016/j.livsci.2011.03.016",
        "title": "Livestock Biodiversity and Sustainability",
        "journal": "Livestock Science",
        "journal_tier": "other",
        "published_date": "2011-07-01",
        "abstract": "Livestock biodiversity is essential for sustainable agriculture. This review examines the role of genetic diversity in livestock adaptation to climate change and emerging diseases.",
        "citation_count": 117,
        "source": "crossref",
        "author": json.dumps([
            {"given": "Irene", "family": "Hoffmann"},
            {"given": "Paul", "family": "Boettcher"}
        ]),
        "keywords": json.dumps(["livestock", "biodiversity", "sustainability", "genetic diversity", "climate change adaptation"]),
        "article_type": "Journal Review",
        "language": "en",
        "volume": "139",
        "issue": "3",
        "page": "145-154",
        "issn": "1871-1413",
        "publisher": "Elsevier",
        "subject": json.dumps(["Animal Science", "Veterinary Science"]),
        "oa_url": "",
        "oa_category": "closed",
        "references_count": 78,
        "external_ids": json.dumps({"crossref": "10.1016/j.livsci.2011.03.016"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
    {
        "doi": "10.1016/j.envres.2024.118503",
        "title": "Biowaste to Bioenergy Nexus: Fostering Sustainability and Circular Economy",
        "journal": "Environmental Research",
        "journal_tier": "other",
        "published_date": "2024-01-01",
        "abstract": "Existing fossil-based commercial products present a significant threat to the depletion of global natural resources. This review explores biowaste valorization pathways for bioenergy production within a circular economy framework.",
        "citation_count": 33,
        "source": "semantic_scholar",
        "author": json.dumps([
            {"given": "Kumar", "family": "Patel"},
            {"given": "Priya", "family": "Singh"}
        ]),
        "keywords": json.dumps(["biowaste", "bioenergy", "circular economy", "sustainability", "waste valorization"]),
        "article_type": "Journal Review",
        "language": "en",
        "volume": "252",
        "issue": "1",
        "page": "118503",
        "issn": "0013-9351",
        "publisher": "Elsevier",
        "subject": json.dumps(["Environmental Science", "Energy"]),
        "oa_url": "",
        "oa_category": "closed",
        "references_count": 120,
        "external_ids": json.dumps({"semantic_scholar": "S123456789"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
    {
        "doi": "10.3389/fmats.2024.1416445",
        "title": "Utilization of Fungal and Bacterial Bioremediation Techniques for the Treatment of Toxic Waste and Biowaste",
        "journal": "Frontiers in Materials",
        "journal_tier": "other",
        "published_date": "2024-01-01",
        "abstract": "The escalating accumulation of toxic wastes and biowastes constitutes a critical environmental crisis. This review focuses on the use of fungal and bacterial strategies in bioremediation, emphasizing their role in degradation, stabilization, or detoxification of pollutants.",
        "citation_count": 59,
        "source": "semantic_scholar",
        "author": json.dumps([
            {"given": "Ahmed", "family": "Hassan"},
            {"given": "Wei", "family": "Chen"}
        ]),
        "keywords": json.dumps(["bioremediation", "fungi", "bacteria", "toxic waste", "biowaste", "environmental crisis"]),
        "article_type": "Journal Review",
        "language": "en",
        "volume": "11",
        "issue": "1",
        "page": "1416445",
        "issn": "2296-8016",
        "publisher": "Frontiers Media",
        "subject": json.dumps(["Materials Science", "Environmental Science"]),
        "oa_url": "https://doi.org/10.3389/fmats.2024.1416445",
        "oa_category": "gold",
        "references_count": 95,
        "external_ids": json.dumps({"semantic_scholar": "S987654321"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
    {
        "doi": "10.1002/aenm.202403142",
        "title": "Unveiling the Critical Role of Pre-Hydrothermal Effect in Plant Biowaste-Derived Hard Carbon for Sodium-Ion Batteries",
        "journal": "Advanced Energy Materials",
        "journal_tier": "other",
        "published_date": "2024-01-01",
        "abstract": "Leveraging economically viable plant bio-waste-derived hard carbon (HC) anode materials for sodium-ion batteries is logical. The resultant OLHC demonstrates high-reversible capacity (378 mAh/g at 0.1C), superior rate performance, and remarkable cycling performance.",
        "citation_count": 63,
        "source": "semantic_scholar",
        "author": json.dumps([
            {"given": "Yuki", "family": "Tanaka"},
            {"given": "Seung", "family": "Kim"},
            {"given": "John", "family": "Miller"}
        ]),
        "keywords": json.dumps(["biowaste", "hard carbon", "sodium-ion batteries", "energy storage", "circular economy"]),
        "article_type": "Journal Article",
        "language": "en",
        "volume": "14",
        "issue": "1",
        "page": "2403142",
        "issn": "1614-6832",
        "publisher": "Wiley",
        "subject": json.dumps(["Materials Science", "Energy"]),
        "oa_url": "",
        "oa_category": "closed",
        "references_count": 67,
        "external_ids": json.dumps({"semantic_scholar": "S555555555"}),
        "meta_json": json.dumps({"_note": "demo data"})
    },
]


def main():
    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()

    # 检查是否已有数据
    cur.execute("SELECT COUNT(*) FROM papers")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"[INFO] 数据库已有 {existing} 条论文记录，跳过示例数据加载")
        print("  如需强制覆盖，请先清空数据库")
        conn.close()
        return

    # 插入示例论文
    for i, paper in enumerate(DEMO_PAPERS, 1):
        cur.execute("""
            INSERT INTO papers (doi, title, journal, journal_tier, published_date,
                abstract, citation_count, source, author, keywords, article_type,
                language, volume, issue, page, issn, publisher, subject, oa_url,
                oa_category, references_count, external_ids, meta_json, is_placeholder)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            paper["doi"], paper["title"], paper["journal"], paper["journal_tier"],
            paper["published_date"], paper["abstract"], paper["citation_count"],
            paper["source"], paper["author"], paper["keywords"], paper["article_type"],
            paper["language"], paper["volume"], paper["issue"], paper["page"],
            paper["issn"], paper["publisher"], paper["subject"], paper["oa_url"],
            paper["oa_category"], paper["references_count"], paper["external_ids"],
            paper["meta_json"]
        ))

    conn.commit()
    print(f"[OK] 已加载 {len(DEMO_PAPERS)} 条示例论文数据")

    # 重建 FTS5 索引
    try:
        cur.execute("DELETE FROM papers_fts")
        cur.execute("INSERT INTO papers_fts(papers_fts) VALUES('rebuild')")
        conn.commit()
        print("[OK] FTS5 索引已重建")
    except Exception as e:
        print(f"[WARN] FTS5 索引重建失败: {e}")

    conn.close()


if __name__ == "__main__":
    main()