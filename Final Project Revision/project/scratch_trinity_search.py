import sys, fitz
import unicodedata
sys.stdout.reconfigure(encoding='utf-8')
doc = fitz.open('Trinity_A_Scalable_and_Forward-Secure_DSSE_for_Spatio-Temporal_Range_Query.pdf')
text = '\n'.join([page.get_text() for page in doc])

# normalize
text = unicodedata.normalize('NFKD', text)

# Find all mentions of "verif" in the text
indices = [i for i in range(len(text)) if text[i:i+5].lower() == 'verif']
print(f"Found {len(indices)} mentions of 'verif'")
for idx in indices:
    snippet = text[max(0,idx-150):idx+300].replace('\n', ' ')
    print(f"\n=== Position {idx} ===")
    print(snippet)
    print("---")
