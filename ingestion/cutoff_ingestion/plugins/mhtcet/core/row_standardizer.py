from typing import Dict

class MHTCETRowStandardizer:
    
    @classmethod
    def decode_category_token(cls, token: str) -> Dict[str, str]:
        token = token.upper().strip()
        
        # Base state fallback
        result = {
            "gender": "General", 
            "category": token, 
            "seat_bucket": "State Level", 
            "is_supernumerary": False
        }

        # 1. Fast-track strict Supernumerary matches
        if token in ["TFWS", "EWS", "ORPHAN"]:
            result["category"] = token
            result["is_supernumerary"] = True
            return result

        working_token = token

        # 2. Peel off the Gender Prefix (L = Ladies, G = General)
        if working_token.startswith("L"):
            result["gender"] = "Female"
            working_token = working_token[1:]
        elif working_token.startswith("G"):
            result["gender"] = "General"
            working_token = working_token[1:]

        # 3. Peel off the Region Suffix (H = Home, O = Other, S = State)
        if working_token.endswith("H"):
            result["seat_bucket"] = "Home University"
            working_token = working_token[:-1]
        elif working_token.endswith("O"):
            result["seat_bucket"] = "Other Than Home University"
            working_token = working_token[:-1]
        elif working_token.endswith("S"):
            result["seat_bucket"] = "State Level"
            working_token = working_token[:-1]

        # 4. Handle PWD/DEF Combinations (e.g., PWDOPEN, DEFOBC)
        if "PWD" in working_token or "DEF" in working_token:
            result["category"] = working_token
            result["is_supernumerary"] = True
            return result
            
        # 5. Final Lossless Category (e.g., "OPEN", "OBC", or "MI" for Minority)
        if working_token:
            result["category"] = working_token
            
        return result