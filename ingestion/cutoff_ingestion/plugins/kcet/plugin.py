from typing import Dict, List, Optional, Any
import unicodedata
from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin
from ingestion.cutoff_ingestion.plugins.kcet.round_normalizer import RoundNormalizer
from ingestion.cutoff_ingestion.plugins.kcet.adapter import KCETContextAdapter
from ingestion.cutoff_ingestion.plugins.kcet.table_parser import KCETTableParser

class KCETPlugin(BaseCutoffPlugin):

    def get_slug(self) -> str:
        return "kcet"

    def get_seed_urls(self) -> Dict[int, str]:
        return {
            2026: "https://cetonline.karnataka.gov.in/kea/ugcet2026",
            2025: "https://cetonline.karnataka.gov.in/kea/ugcet2025",
            2024: "https://cetonline.karnataka.gov.in/kea/ugcet2024",
            2023: "https://cetonline.karnataka.gov.in/kea/cet2023"
        }

    def get_container_tags(self) -> List[str]:
        return ['div', 'tr']
    
    def get_request_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,kn;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def get_notification_filters(self) -> Dict[str, List[str]]:
        return {
            "positive": [
                "CUTOFF", "CUT-OFF", "ಕಟ್ ಆಫ್", "ಕಟ್ಆಫ್", "ಕಟ್‌ಆಫ್"
            ],
            "negative": [
                "ALLOTMENT", "RESULT", "SCHEDULE", "FEE", "MATRIX", "KEY", 
                "PRESS", "VERIFICATION", "CHALLAN", "NOTE", "PAYMENT", 
                "DATE EXTENSION", "INSTRUCTION", "SUMMARY", "PROCEDURE",
                # MANDATORY KANNADA NEGATIVES
                "ಪರಿಶೀಲನಾ", "ದಿನಾಂಕ", "ಶುಲ್ಕ", "ಅರ್ಜಿ", "ಮಾಹಿತಿ",
                "ವೇಳಾಪಟ್ಟಿ", "ಆಯ್ಕೆ", "ಎಂಟ್ರಿ", "ಸಕ್ರಿಯ", "ಪ್ರವೇಶ", "ವಿಸ್ತರಣೆ",
                "ಪಾವತಿ", "ಆದೇಶ", "ಅಧಿಸೂಚನೆ", "ತಾತ್ಕಾಲಿಕ", "ಅಡ್ಮಿಷನ್", "ಪ್ರಕಟಣೆ", 
                "ಅಣಕು", "ಅರ್ಹತಾ", "ಪ್ರಾವಿಶನಲ್", "PROVISIONAL"
            ]
        }

    def get_child_filters(self) -> List[str]:
        return self.get_notification_filters()["negative"] + [
            "LINK", "ಲಿಂಕ್", "CHOICE", "ENTRY", "MATRIX", "ಹಂಚಿಕೆ", "ಶುಲ್ಕ"
        ]

    def normalize_round(self, text: str) -> Optional[int]:
        return RoundNormalizer.normalize(text)

    def normalize_artifact_name(self, text: str) -> tuple[str, str, bool]:
        """
        Enterprise-grade standardization using pure Python logic (No Regex).
        Fixed for: Combined courses, Yoga/Practical confusion, and Science suffixes.
        """
        if not text: return "", "", False
        
        # Normalize: Upper case, strip spaces, standard unicode
        upper_text = unicodedata.normalize('NFC', text).upper().strip()
        
        clean_parts = []
        is_standardized = True

        # --- KEYWORD DEFINITIONS ---
        k_bpharma = ["B.PHARMA", "B.PHARM", "ಬಿ-ಫಾರ್ಮಾ", "ಬಿ. ಫಾರ್ಮಾ", "ಬಿ-ಫಾರ್ಮ", "ಬಿ.ಫಾರ್ಮಾ"]
        k_pharmd = ["PHARMA-D", "PHARM-D", "PHARMA.D", "PHARM.D", "ಫಾರ್ಮ್-ಡಿ", "ಫಾರ್ಮ್ - ಡಿ", "ಫಾರ್ಮಾ - ಡಿ", "ಫಾರ್ಮಾ-ಡಿ"]
        k_agri = ["AGRICULTURE", "ಕೃಷಿ"] 
        k_vet = ["VETERINARY", "ವೆಟರ್ನರಿ", "ಪಶುವೈದ್ಯಕೀಯ"]
        k_eng = ["ENGINEERING", "ಇಂಜಿನಿಯರಿಂಗ್", "ಎಂಜಿನಿಯರಿಂಗ್"]
        k_arch = ["ARCHITECTURE", "ವಾಸ್ತುಶಿಲ್ಪ", "ಆರ್ಕಿಟೆಕ್ಚರ್"]
        k_nursing = ["NURSING", "ನರ್ಸಿಂಗ್"]
        # Yoga: Strict check keywords to avoid matching 'Prayogika'
        k_yoga_strict = ["NATUROPATHY", "ಪ್ರಕೃತಿ", "YOGA &", "YOGA AND", "ಯೋಗ ಮತ್ತು"]
        k_science = ["SCIENCE", "ವಿಜ್ಞಾನ", "ಸೈನ್ಸ್"]
        k_bsc = ["B.SC", "BSC", "ಬಿ.ಎಸ್ಸಿ", "ಬಿಎಸ್ಸಿ"]
        k_food = ["FOOD", "ಆಹಾರ", "ಫುಡ್"]
        k_fish = ["FISHERIES", "ಮೀನುಗಾರಿಕೆ"]
        k_farm = ["FARM", "ಫಾರ್ಮ್"]
        k_record = ["RECORD", "ದಾಖಲೆ", "ರೆಕಾರ್ಡ್"]
        k_bpt = ["BPT", "ಬಿಪಿಟಿ"]
        k_bpo = ["BPO", "ಬಿಪಿಓ"]
        k_ahs = ["AHS", "ಎ ಹೆಚ್ ಎಸ್", "ಅಲೈಡ್ ಹೆಲ್ತ್"]

        # Check presence
        is_bpharma = any(x in upper_text for x in k_bpharma)
        is_pharmd = any(x in upper_text for x in k_pharmd)
        is_agri = any(x in upper_text for x in k_agri)
        is_vet = any(x in upper_text for x in k_vet)
        is_eng = any(x in upper_text for x in k_eng)
        is_arch = any(x in upper_text for x in k_arch)
        is_nursing = any(x in upper_text for x in k_nursing)
        is_yoga = any(x in upper_text for x in k_yoga_strict)
        is_farm = any(x in upper_text for x in k_farm)
        is_food = any(x in upper_text for x in k_food)
        is_fish = any(x in upper_text for x in k_fish)
        is_bsc = any(x in upper_text for x in k_bsc)
        is_science = any(x in upper_text for x in k_science)

        # Flags to prevent duplicates
        done_agri = False
        done_farm = False
        done_arch = False

        # --- 1. COMBINED & PRIORITY COURSE LOGIC ---

        # B.Pharma & Pharm-D
        if is_bpharma and is_pharmd:
            clean_parts.append("B.Pharma & Pharm-D")
        elif is_bpharma:
            clean_parts.append("B.Pharma")
        elif is_pharmd:
            clean_parts.append("Pharm-D")

        # Agriculture & Farm Science (2024 Case)
        elif is_agri and is_farm:
            clean_parts.append("Agriculture & Farm Science")
            done_agri = True
            done_farm = True

        # Agriculture & Veterinary (2023 Case)
        elif is_agri and is_vet:
            clean_parts.append("Agriculture & Veterinary")
            done_agri = True
            # Veterinary handled here

        # Food Science & Fisheries
        elif is_food and is_fish:
            clean_parts.append("Food Science & Fisheries")
        
        elif is_food:
            clean_parts.append("Food Science")
        
        elif is_fish:
            clean_parts.append("Fisheries")

        # Engineering Block (Handles Agriculture Eng & Arch Eng)
        elif is_eng:
            if is_arch:
                clean_parts.append("Architecture Engineering")
                done_arch = True
            elif is_agri:
                clean_parts.append("Agriculture Engineering")
                done_agri = True
            else:
                clean_parts.append("Engineering")

        # Farm Science (Stand-alone)
        elif is_farm and not done_farm:
            clean_parts.append("Farm Science")
            # If Farm Science exists, ignore generic Agriculture (often triggered by 'Krushika' quota)
            done_agri = True 

        # Agriculture (Stand-alone)
        elif is_agri and not done_agri:
            name = "Agriculture"
            if is_science: name += " Science" # Fix: Add Science suffix if present
            if is_bsc: name = "B.Sc " + name # Fix: Add B.Sc prefix if present
            clean_parts.append(name)

        # Veterinary (Stand-alone)
        elif is_vet and not (is_agri): # If not handled by Agri&Vet
            name = "Veterinary"
            if is_science: name += " Science"
            clean_parts.append(name)

        # Architecture (Stand-alone)
        elif is_arch and not done_arch:
            clean_parts.append("Architecture")

        # Nursing
        elif is_nursing:
            name = "Nursing"
            if is_bsc: name = "B.Sc " + name
            clean_parts.append(name)

        # Yoga & Naturopathy
        elif is_yoga:
            clean_parts.append("Yoga & Naturopathy")

        # Paramedical
        elif any(x in upper_text for x in k_record):
            clean_parts.append("Medical Record Technology")
        elif any(x in upper_text for x in k_bpt):
            clean_parts.append("BPT")
        elif any(x in upper_text for x in k_bpo):
            clean_parts.append("BPO")
        elif any(x in upper_text for x in k_ahs):
            clean_parts.append("B.Sc AHS")

        # Fallback
        elif not clean_parts: # Only if nothing matched so far
            clean_parts.append(text.strip())
            is_standardized = False

        # --- 2. ATTRIBUTE TAGGING ---
        
        if any(x in upper_text for x in ["PRACTICAL", "ಪ್ರಾಯೋಗಿಕ", "ಪ್ರಾಕ್ಟಿಕಲ್"]): 
            clean_parts.append("(Practical)")

        if any(x in upper_text for x in ["THEORY", "ಥಿಯರಿ"]): 
            clean_parts.append("(Theory)")

        if any(x in upper_text for x in ["HK", "H.K", "HYD", "HYDERABAD"]): 
            clean_parts.append("(HK)")

        if any(x in upper_text for x in ["GENERAL", "GEN", "ಸಾಮಾನ್ಯ"]): 
            clean_parts.append("(General)")
            
        if any(x in upper_text for x in ["PRIVATE", "PVT"]): 
            clean_parts.append("(Private)")
            
        if any(x in upper_text for x in ["AGRICULTURIST", "ಕೃಷಿಕ"]): 
            clean_parts.append("(Agriculturist Quota)")
            
        if any(x in upper_text for x in ["SPECIAL", "ವಿಶೇಷ", "SPL"]): 
            clean_parts.append("(Special)")

        # --- 3. DEDUPLICATION & CLEANUP ---
        if not is_standardized:
            return text.strip(), text.strip(), False

        # Remove duplicates while preserving order
        seen = set()
        deduped = [x for x in clean_parts if not (x in seen or seen.add(x))]
        
        return " ".join(deduped), text.strip(), is_standardized

    def get_adapter(self) -> Any:
        return KCETContextAdapter()

    def get_parser(self, pdf_path: str) -> Any:
        return KCETTableParser(pdf_path)