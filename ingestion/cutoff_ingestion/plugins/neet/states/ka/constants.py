import re

def compile_flex(text: str) -> re.Pattern:
    base = re.sub(r'\s+', r'[\\s\\-_]+', text.strip())
    return re.compile(rf'\b{base}\b', re.IGNORECASE)

# --- 1. CONTEXT ANCHORS ---
P_UGNEET = re.compile(r'(?:UG[\s\-_]*NEET|ಯುಜಿ[\s\-_]*ನೀಟ್)', re.IGNORECASE)
P_UGCET  = re.compile(r'(?:UG[\s\-_]*CET|ಯುಜಿಸಿಇಟಿ)', re.IGNORECASE) 
P_UGAYUSH = re.compile(r'(?:UG[\s\-_]*AYUSH|ಯುಜಿ[\s\-_]*ಆಯುಷ್)', re.IGNORECASE)
P_UGDENTAL = re.compile(r'(?:UG[\s\-_]*DENTAL|ಯುಜಿ[\s\-_]*ದಂತ)', re.IGNORECASE)

P_MEDICAL = re.compile(r'(?:MEDICAL|ವೈದ್ಯಕೀಯ)', re.IGNORECASE)
P_DENTAL  = re.compile(r'(?:DENTAL|ದಂತ|BDS)', re.IGNORECASE)
P_AYUSH   = re.compile(r'(?:AYUSH|ಆಯುಷ್|ISMH)', re.IGNORECASE)

# --- 2. SEMANTIC ANCHORS ---
P_ALLOT   = re.compile(r'(?:ALLOTMENT|SELECTION|RESULT|ಹಂಚಿಕೆ|ಫಲಿತಾಂಶ|ಪಲಿತಾಂಶ|ಪಟ್ಟಿ)', re.IGNORECASE)

# Handles Kannada Zero-Width Joiners/Non-Joiners
P_CUTOFF  = re.compile(r'(?:CUTOFF|CUT[_\-\s]OFF|ಕಟ್[\s\-_\u200c\u200d]*ಆಫ್)', re.IGNORECASE)

# --- 3. ROUND DETECTION ---
P_ROUND_1 = re.compile(r'(?:FIRST|ROUND[_\-\s]?1|ROUND[_\-\s]?I\b|MODALA|ಒಂದನೇ|ಮೊದಲ|1ನೇ|1ನೆ)', re.IGNORECASE)
P_ROUND_2 = re.compile(r'(?:SECOND|ROUND[_\-\s]?2|ROUND[_\-\s]?II\b|ERADANE|ಎರಡನೇ|2ನೇ|2ನೆ)', re.IGNORECASE)
P_ROUND_3 = re.compile(r'(?:THIRD|ROUND[_\-\s]?3|ROUND[_\-\s]?III\b|MOORANE|ಮೂರನೇ|3ನೇ|3ನೆ)', re.IGNORECASE)

P_MOPUP   = re.compile(r'(?:MOP[_\-\s]?UP|ಮಾಪ್)', re.IGNORECASE)
P_STRAY   = re.compile(r'(?:STRAY|ಸ್ಟ್ರೇ|ಸ್ಟ್ರೆ)', re.IGNORECASE)
P_SPECIAL = re.compile(r'(?:SPECIAL|VISHESHA|ವಿಶೇಷ)', re.IGNORECASE)

# --- 4. TRASH FILTERS ---
HARD_TRASH = [
    compile_flex("FEE"), re.compile(r'ಶುಲ್ಕ', re.IGNORECASE),
    compile_flex("REFUND"), re.compile(r'ಮರುಪಾವತಿ', re.IGNORECASE),
    compile_flex("CHALLAN"), re.compile(r'ಚಲನ್', re.IGNORECASE),
    compile_flex("BANK"), 
    compile_flex("VERIFICATION"), re.compile(r'ಪರಿಶೀಲನೆ', re.IGNORECASE),
    compile_flex("ELIGIBILITY"), re.compile(r'ಅರ್ಹತಾ', re.IGNORECASE),
    compile_flex("NON-KARNATAKA"), compile_flex("CANCEL"),
    compile_flex("WITHHELD"), compile_flex("CAUTION DEPOSIT"),
    compile_flex("PGET"),
    
    # Legal & Court Orders 
    compile_flex("COURT"), re.compile(r'ನ್ಯಾಯಾಲಯ', re.IGNORECASE),
    compile_flex("ORDER"), re.compile(r'ಆದೇಶ', re.IGNORECASE),
    compile_flex("SLP"), re.compile(r'ಎಸ್[\s\-]*ಎಲ್[\s\-]*ಪಿ', re.IGNORECASE),
    compile_flex("WRIT"),

    # [NEW] Candidates & Reporting (Blocks Unreported/Not-Joined Lists)
    compile_flex("REPORT"), re.compile(r'ವರದಿ', re.IGNORECASE), 
    compile_flex("CANDIDATE"), re.compile(r'ಅಭ್ಯರ್ಥಿ', re.IGNORECASE), 

    # [NEW] Option Entry (Blocks schedule extensions)
    compile_flex("OPTION"), re.compile(r'ಆಯ್ಕೆ', re.IGNORECASE), 
    compile_flex("ENTRY"), re.compile(r'ನಮೂದು', re.IGNORECASE), 
]

SOFT_TRASH = [
    compile_flex("NOTE"), re.compile(r'ಟಿಪ್ಪಣಿ', re.IGNORECASE), 
    compile_flex("CIRCULAR"), re.compile(r'ಪ್ರಕಟಣೆ', re.IGNORECASE), 
    compile_flex("SCHEDULE"), re.compile(r'ವೇಳಾಪಟ್ಟಿ', re.IGNORECASE), 
    compile_flex("GUIDELINE"), re.compile(r'ಮಾರ್ಗಸೂಚಿ', re.IGNORECASE),
    compile_flex("INSTRUCTION"), re.compile(r'ಸೂಚನೆ', re.IGNORECASE),
    compile_flex("MOCK"), re.compile(r'ಅಣಕು', re.IGNORECASE), 
    
    # Date Extensions & Info
    re.compile(r'(?:DATE|TIME)\s*EXTENDED', re.IGNORECASE),
    re.compile(r'ದಿನಾಂಕ.*ವಿಸ್ತರಿಸ', re.IGNORECASE), 
    re.compile(r'ವಿಸ್ತರಿಸ', re.IGNORECASE), 
    re.compile(r'ವಿಸ್ತರಣೆ', re.IGNORECASE), # Vistarane (Extension)
    
    # [NEW] Information (Blocks "Further Information" notices)
    compile_flex("INFORMATION"), re.compile(r'ಮಾಹಿತಿ', re.IGNORECASE), 
    
    # Administrative & Procedural Noise
    re.compile(r'POST.*ALLOTMENT', re.IGNORECASE),
    re.compile(r'ಪೋಸ್ಟ್.*ಹಂಚಿಕೆ', re.IGNORECASE),
    re.compile(r'ಅಪ್[\s\-_\u200c\u200d]*ಡೇಟ್', re.IGNORECASE), 
    re.compile(r'ಪ್ರಕ್ರಿಯೆ', re.IGNORECASE), 
    re.compile(r'ಕಾರ್ಯವಿಧಾನ', re.IGNORECASE), 
    re.compile(r'ಸಂಬಂಧಿಸಿದಂತೆ', re.IGNORECASE), 
    re.compile(r'ಕುರಿತು', re.IGNORECASE), 
    
    # Provisional Filters 
    compile_flex("PROVISIONAL"), 
    re.compile(r'ತಾತ್ಕಾಲಿಕ', re.IGNORECASE), 
    re.compile(r'ಪ್ರಾವಿ[ಶಷ]ನಲ್', re.IGNORECASE) 
]

P_HEADER_CLASS = re.compile(r"header", re.IGNORECASE)