import re
from typing import Optional

class RoundNormalizer:
    """
    Standardizes KCET Round text to Integers.
    Strictly enforcing 2023-2025 semantics.
    """
    PATTERNS = [
        (r'MOCK|ಅಣಕು', 0),
        
        # Extended Rounds (Priority over standard numbers)
        (r'SECOND\s+EXTENDED|ಎರಡನೇ\s+ವಿಸ್ತೃತ|ಎರಡನೇ\s+ವಿಸ್ತ್ರತ', 3), 
        (r'SPECIAL|ವಿಶೇಷ', 4),
        
        # Standard Rounds
        (r'FIRST|ಮೊದಲ|ಒಂದು', 1),
        (r'SECOND|ಎರಡನೇ|ಎರಡು', 2),
        (r'THIRD|ಮೂರನೇ|ಮೂರು', 3),
        (r'FOURTH|ನಾಲ್ಕನೇ|ನಾಲ್ಕು', 4)
    ]

    @classmethod
    def normalize(cls, text: str) -> Optional[int]:
        if not text: return None
        upper_text = text.upper().strip()
        
        # 1. Regex Pattern Matching (Keywords)
        for pattern, value in cls.PATTERNS:
            if re.search(pattern, upper_text, re.IGNORECASE):
                return value
        
        # 2. Fallback: Direct Digit Search (e.g. "Round 1", "R2")
        # Strict Boundary \b ensures we don't match "2024" as "2" or "4"
        match = re.search(r'\b(1|2|3|4)\b', upper_text)
        if match: return int(match.group(1))
                
        # 3. FAILURE: Do not default. Return None to signal Rejection.
        return None