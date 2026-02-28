import re

# --- 1. ROMAN NUMERAL NORMALIZATION ---
ROUND_MAP = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6
}

# --- 2. DYNAMIC ROUND DETECTION ---
# Fixed: Longer Roman numerals placed first to prevent partial 'I' matches from 'IV'
P_ROUND = re.compile(r'ROUND\s*((?:IV|V|VI|I{1,3})|\d+)', re.IGNORECASE)

# --- 3. COMPOUND GATES ---
P_CUTOFF = re.compile(r'CUTOFF', re.IGNORECASE)

# [CRITICAL] Blocks legacy files, vacancy lists, and raw allotment dumps. 
# Replaced generic 'FINAL' with explicit 'FINAL MERIT' and 'FINAL LIST' to prevent dropping real final rounds.
P_BLOCK = re.compile(
    r'(LIST OF CANDIDATES|FINAL MERIT|FINAL LIST|SEAT MATRIX|VACANCY|BROCHURE|A\.Y\.|INSTITUTE WISE)',
    re.IGNORECASE
)