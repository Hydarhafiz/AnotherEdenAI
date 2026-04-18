import pandas as pd
import ast
import random

# --- CONFIGURATION ---
TARGET_CHAR = "Rufus"  # Change this to "Tsukiha", "Aldo", etc.
FILES = {
    "chars": "ae_characters.csv",
    "grasta": "ae_grasta_master.csv",
    "ores": "ae_ores.csv"
}

def load_data():
    print(f"--- Loading Data to Analyze {TARGET_CHAR} ---")
    df_c = pd.read_csv(FILES["chars"])
    df_g = pd.read_csv(FILES["grasta"])
    df_o = pd.read_csv(FILES["ores"])
    
    # Clean list parsing
    try:
        df_c['personalities'] = df_c['personalities'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else [])
    except: pass
    
    return df_c, df_g, df_o

def get_meta_build(char_name, df_c, df_g, df_o):
    # 1. FIND THE CHARACTER
    char_row = df_c[df_c['name'].str.contains(char_name, case=False, na=False)]
    if char_row.empty:
        return f"Error: Character '{char_name}' not found."
    
    # Get the specific data
    row = char_row.iloc[0]
    traits = row['personalities']
    weapon = row['weapon']
    print(f"\nFound: {row['name']}")
    print(f"Traits: {traits}")
    
    # 2. FIND PERSONALITY GRASTAS (The "Mule" Grastas)
    # Logic: Find Shareable Grastas that match the character's traits
    # (These are buffs other people should carry for him)
    shareables = df_g[
        (df_g['is_shareable'] == True) & 
        (df_g['personality_req'].isin(traits))
    ]
    
    # 3. FIND SELF-BUFF GRASTAS (The "DPS" Grastas)
    # Logic: Pain/Poison Grastas matching his Weapon
    # (Note: In your scraper, weapon grastas often have 'data-weapon' attributes or are generic)
    # For this demo, we look for T2 Grastas that match his weapon type or element
    self_buffs = df_g[
        (df_g['tier'].astype(str).isin(['2', '3'])) &
        (df_g['is_shareable'] == False) &
        (df_g['name'].str.contains(weapon, case=False, na=False) | 
         df_g['name'].str.contains("Pain", case=False)) 
    ].head(3) # Just grab top 3 for demo

    # 4. PICK ORES (The Enhancements)
    # In a real AI, this would be complex logic. For now, we pick the "Meta" ores.
    # Typically: Bull's Eye (for DPS), Rose with Thorns (for DPS)
    meta_ores = ["Bull's Eye Ore", "Rose with Thorns Ore", "Last Stand Ore"]
    found_ores = df_o[df_o['name'].isin(meta_ores)]
    
    # --- GENERATE REPORT ---
    print("\n" + "="*40)
    print(f" OPTIMIZED BUILD STRATEGY FOR {row['name'].upper()} ")
    print("="*40)
    
    print(f"\n[1] THE 'MULE' SETUP (Party Buffs)")
    print(f"   *Assign these Grastas to your Supports (e.g. Aldo, Strawboy)*")
    if not shareables.empty:
        for idx, g in shareables.iterrows():
            print(f"   - {g['name']} (Req: {g['personality_req']})")
            print(f"     -> Effect: {g['stats']}")
    else:
        print("   - No Shareable Personality Grastas found for this character.")

    print(f"\n[2] THE 'SELF' SETUP (Equip on {row['name']})")
    print(f"   *Standard DPS configuration*")
    for idx, g in self_buffs.iterrows():
        # Pair with an Ore
        ore_name = meta_ores[idx % len(meta_ores)] if meta_ores else "Any Ore"
        print(f"   - {g['name']} <ENHANCED WITH> {ore_name}")

# --- RUN ---
if __name__ == "__main__":
    c, g, o = load_data()
    get_meta_build(TARGET_CHAR, c, g, o)