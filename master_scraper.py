import requests
from bs4 import BeautifulSoup
import pandas as pd
import ast

# --- CONFIGURATION ---
URLS = {
    "characters": "https://anothereden.wiki/w/Characters",
    "grasta_attack": "https://anothereden.wiki/w/Grasta_Attack",
    "grasta_life": "https://anothereden.wiki/w/Grasta_Life",
    "grasta_support": "https://anothereden.wiki/w/Grasta_Support",
    "grasta_special": "https://anothereden.wiki/w/Grasta_Special",
    "grasta_vc": "https://anothereden.wiki/w/Grasta_VC",
    "grasta_ores": "https://anothereden.wiki/w/Grasta_Ores"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_soup(url):
    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# --- SCRAPERS ---

def scrape_characters():
    soup = get_soup(URLS["characters"])
    if not soup: return []
    data = []
    rows = soup.find_all("tr", class_="character-row-entry")
    
    print(f"Parsing {len(rows)} characters...")
    for row in rows:
        try:
            p_str = row.get("data-personality", "")
            personalities = [p.strip() for p in p_str.split(",") if p.strip()]
            
            data.append({
                "name": row.get("data-name"),
                "element": row.get("data-element"),
                "weapon": row.get("data-weapon"),
                "light_shadow": row.get("data-type"),
                "personalities": personalities
            })
        except: continue
    return pd.DataFrame(data)

def scrape_grasta_general(category, url):
    soup = get_soup(url)
    if not soup: return []
    data = []
    rows = soup.find_all("tr", class_="grasta-row-entry")
    
    print(f"Parsing {len(rows)} {category} grastas...")
    for row in rows:
        try:
            cols = row.find_all("td")
            stats_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""

            data.append({
                "name": row.get("data-name"),
                "category": category,
                "tier": row.get("data-tier"),
                "stats": stats_text,
                "personality_req": row.get("data-personality"),
                "is_shareable": row.get("data-share") == "1"
            })
        except: continue
    return pd.DataFrame(data)

def scrape_vc_grasta():
    soup = get_soup(URLS["grasta_vc"])
    if not soup: return []
    data = []
    rows = soup.find_all("tr", class_="grasta-row-entry")
    
    print(f"Parsing {len(rows)} VC grastas...")
    for row in rows:
        try:
            data.append({
                "name": row.get("data-name"),
                "category": "VC",
                "tier": 4,
                "stats": "VC Upgrade",
                "personality_req": row.get("data-personality"),
                "is_shareable": False
            })
        except: continue
    return pd.DataFrame(data)

def scrape_ores():
    # FIX: Uses 'equip-row-entry' based on your HTML snippet
    soup = get_soup(URLS["grasta_ores"])
    if not soup: return []
    data = []
    rows = soup.find_all("tr", class_="equip-row-entry")
    
    print(f"Parsing {len(rows)} Ores...")
    for row in rows:
        try:
            cols = row.find_all("td")
            if len(cols) < 3: continue
            
            # Name is often in the 2nd column (index 1) inside an anchor tag
            name_tag = cols[1].find("a")
            name = name_tag.get_text(strip=True) if name_tag else cols[1].get_text(strip=True)
            
            # Stats/Effect is in the 3rd column (index 2)
            stats = cols[2].get_text(" ", strip=True)
            
            # Source/Location is usually in the 4th column (index 3)
            source = cols[3].get_text(" ", strip=True) if len(cols) > 3 else "Unknown"

            data.append({
                "name": name,
                "category": "Ore",
                "stats": stats,
                "source": source
            })
        except: continue
    return pd.DataFrame(data)

# --- SCHEMA GENERATOR ---
def generate_updated_schema(df_chars, df_grasta, df_ores):
    print("\n=== AUTOMATED KG SCHEMA DESIGN (UPDATED) ===")
    
    # Helper to get types
    def get_col_types(df):
        return {col: str(df[col].dtype) for col in df.columns}

    char_cols = get_col_types(df_chars)
    grasta_cols = get_col_types(df_grasta)
    ore_cols = get_col_types(df_ores)
    
    mermaid_code = f"""
classDiagram
    class Character {{
        {char_cols.get('name')} name (PK)
        {char_cols.get('element')} element
        {char_cols.get('weapon')} weapon
        {char_cols.get('light_shadow')} light_shadow
    }}
    
    class Trait {{
        string name (PK)
    }}
    
    class Grasta {{
        {grasta_cols.get('name')} name (PK)
        {grasta_cols.get('category')} category
        {grasta_cols.get('tier')} tier
        {grasta_cols.get('stats')} stats
        {grasta_cols.get('is_shareable')} is_shareable
    }}

    class Ore {{
        {ore_cols.get('name')} name (PK)
        {ore_cols.get('stats')} stats
        {ore_cols.get('source')} source
    }}

    %% Relationships
    Character "1" --> "M" Trait : HAS_TRAIT
    Grasta "1" --> "1" Trait : REQUIRES_TRAIT
    Ore "1" --> "M" Grasta : ENHANCES
    """
    
    print("\n--- Mermaid.js Code (Copy this to a viewer) ---")
    print(mermaid_code)
    print("-----------------------------------------------")

# --- EXECUTION ---
if __name__ == "__main__":
    # 1. Scrape All
    df_chars = scrape_characters()
    
    df_atk = scrape_grasta_general("Attack", URLS["grasta_attack"])
    df_life = scrape_grasta_general("Life", URLS["grasta_life"])
    df_sup = scrape_grasta_general("Support", URLS["grasta_support"])
    df_spl = scrape_grasta_general("Special", URLS["grasta_special"])
    df_vc = scrape_vc_grasta()
    
    df_grasta_master = pd.concat([df_atk, df_life, df_sup, df_spl, df_vc], ignore_index=True)
    
    df_ores = scrape_ores()
    
    # 2. Save
    df_chars.to_csv("ae_characters.csv", index=False)
    df_grasta_master.to_csv("ae_grasta_master.csv", index=False)
    df_ores.to_csv("ae_ores.csv", index=False)
    
    print("\nSUCCESS! Files Generated:")
    print(f"1. ae_characters.csv ({len(df_chars)} rows)")
    print(f"2. ae_grasta_master.csv ({len(df_grasta_master)} rows)")
    print(f"3. ae_ores.csv ({len(df_ores)} rows)")
    
    # 3. Generate Design
    if not df_chars.empty and not df_grasta_master.empty and not df_ores.empty:
        generate_updated_schema(df_chars, df_grasta_master, df_ores)