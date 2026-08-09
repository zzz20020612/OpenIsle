import sys, json
sys.path.insert(0, r"d:\Seadrive\吴相民 6020\我的资料库\Research\文献系统\code")
from utils import get_journal_tier

test = ["Nature", "Science", "Cell", "The Lancet", "PNAS",
        "Nature Communications", "Nature Sustainability", "Science Advances",
        "Environmental Science & Technology", "Water Research",
        "Scientific Reports", "PLOS ONE", "Proceedings of 12th World Congress on Genetics Applied to Livestock Production (WCGALP)",
        "Livestock Science", "Livestock Production Science", "Journal of Dairy Science",
        "Preventive Veterinary Medicine", "The Rangeland Journal"]

print(f"{'期刊名':<70} | {'tier'}")
print("-" * 90)
for j in test:
    print(f"  {j:<68} | {get_journal_tier(j)}")

# 看 _load_journal_tiers 实际加载到的内容
from utils import _load_journal_tiers
data = _load_journal_tiers()
print("\n=== 实际加载到的 tier1 ===")
for t in data.get("tier1", []):
    print("  -", t)
print("\n=== 实际加载到的 tier2 (前10) ===")
for t in data.get("tier2", [])[:10]:
    print("  -", t)
