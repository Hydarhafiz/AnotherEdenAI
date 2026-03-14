"""Temporary diagnostic script to count live Grasta rows per wiki category.

Counts raw wiki rows AND unique names (what Neo4j stores after MERGE by name).
Read-only — does not touch Neo4j or modify any data.
"""
import httpx
from bs4 import BeautifulSoup
from collections import Counter

URLS = {
    "Attack":  "https://anothereden.wiki/w/Grasta_Attack",
    "Life":    "https://anothereden.wiki/w/Grasta_Life",
    "Support": "https://anothereden.wiki/w/Grasta_Support",
    "Special": "https://anothereden.wiki/w/Grasta_Special",
    "VC":      "https://anothereden.wiki/w/Grasta_VC",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (AnotherEdenAI-research-bot)"}


def get_names(url: str, is_vc: bool = False) -> list[str]:
    resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    names = []
    for tr in soup.select("tr.grasta-row-entry"):
        cols = tr.find_all("td")
        if len(cols) < 4:
            continue
        if is_vc:
            name = cols[1].get_text(strip=True)
        else:
            name = tr.get("data-name", "")
        if name:
            names.append(name)
    return names


all_names: list[str] = []
print(f"{'Category':<10} {'Rows':>6} {'Unique':>8} {'Dupes':>7}")
print("-" * 35)

category_data = {}
for category, url in URLS.items():
    is_vc = (category == "VC")
    names = get_names(url, is_vc=is_vc)
    unique = len(set(names))
    dupes = len(names) - unique
    category_data[category] = names
    all_names.extend(names)
    print(f"{category:<10} {len(names):>6} {unique:>8} {dupes:>7}")

total_rows = len(all_names)
total_unique = len(set(all_names))
total_dupes = total_rows - total_unique

print("-" * 35)
print(f"{'TOTAL':<10} {total_rows:>6} {total_unique:>8} {total_dupes:>7}")
print()
print(f"Wiki rows              : {total_rows}")
print(f"Unique names (neo4j)   : {total_unique}")
print(f"Deduplicated by MERGE  : {total_dupes}")
print()

# Show top duplicates across all categories
name_counts = Counter(all_names)
dupe_names = {n: c for n, c in name_counts.items() if c > 1}
if dupe_names:
    print(f"Top duplicate names (count > 1): {len(dupe_names)} names shared across categories")
    for name, count in sorted(dupe_names.items(), key=lambda x: -x[1])[:20]:
        # Find which categories have this name
        cats = [c for c, names in category_data.items() if name in names]
        print(f"  {count}x  {name!r:<40}  [{', '.join(cats)}]")
else:
    print("No duplicate names found across categories.")
