import pandas as pd
import ast

# 1. Load the data you just scraped
df_chars = pd.read_csv("ae_characters.csv")
df_grasta = pd.read_csv("ae_grasta_master.csv")

print("Extracting unique traits...")

# 2. Collect traits from Characters
# (The scraper saved them as string representations of lists "['A', 'B']", so we parse them back)
char_traits = set()
for p_str in df_chars['personalities']:
    try:
        # distinct traits from characters
        p_list = ast.literal_eval(p_str)
        for p in p_list:
            char_traits.add(p.strip())
    except:
        continue

# 3. Collect traits from Grasta Requirements
grasta_traits = set()
for p in df_grasta['personality_req'].dropna():
    # distinct traits from grasta
    grasta_traits.add(p.strip())

# 4. Merge them (The "Union")
# This is important because sometimes a Grasta exists for a trait, 
# but maybe no character has it yet (or vice versa).
all_traits = char_traits.union(grasta_traits)

# 5. Save the Master Trait List
df_traits = pd.DataFrame(sorted(list(all_traits)), columns=["name"])
df_traits.to_csv("ae_traits.csv", index=False)

print(f"SUCCESS! Generated 'ae_traits.csv' with {len(df_traits)} unique traits.")
print("Sample:", list(all_traits)[:5])