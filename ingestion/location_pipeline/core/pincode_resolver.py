import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# --- GEOGRAPHIC STANDARDIZER (ISO 3166-2:IN) ---
STATE_MAP_CONSTANT = {
    # States (28)
    "ANDHRA PRADESH": "AP", "ARUNACHAL PRADESH": "AR", "ASSAM": "AS", 
    "BIHAR": "BR", "CHHATTISGARH": "CG", "GOA": "GA", "GUJARAT": "GJ", 
    "HARYANA": "HR", "HIMACHAL PRADESH": "HP", "JHARKHAND": "JH", 
    "KARNATAKA": "KA", "KERALA": "KL", "MADHYA PRADESH": "MP", 
    "MAHARASHTRA": "MH", "MANIPUR": "MN", "MEGHALAYA": "ML", 
    "MIZORAM": "MZ", "NAGALAND": "NL", "ODISHA": "OD", "PUNJAB": "PB", 
    "RAJASTHAN": "RJ", "SIKKIM": "SK", "TAMIL NADU": "TN", "TELANGANA": "TS", 
    "TRIPURA": "TR", "UTTAR PRADESH": "UP", "UTTARAKHAND": "UK", "WEST BENGAL": "WB",
    
    # Union Territories (8)
    "ANDAMAN AND NICOBAR ISLANDS": "AN", "CHANDIGARH": "CH", 
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "DH", 
    "DADRA AND NAGAR HAVELI": "DN", "DAMAN AND DIU": "DD", 
    "DELHI": "DL", "JAMMU AND KASHMIR": "JK", "LADAKH": "LA", 
    "LAKSHADWEEP": "LD", "PUDUCHERRY": "PY"
}

class PincodeResolver:
    """
    O(1) In-Memory Geographic Decoder.
    Transforms raw JSON array into a hyper-fast hashmap on worker boot.
    """
    _instance = None
    _dataset: Dict[str, Dict[str, str]] = {}
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PincodeResolver, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self._load_dataset()

    def _load_dataset(self):
        # Deterministic Path Resolution mapped to your VS Code Workspace
        # __file__       = ingestion/location_pipeline/core/pincode_resolver.py
        # parent 1       = core/
        # parent 2       = location_pipeline/
        # parent 3       = ingestion/
        
        current_path = Path(__file__).resolve()
        ingestion_dir = current_path.parent.parent.parent 
        file_path = ingestion_dir / "assets" / "pincodes.json"

        if not file_path.exists():
            logger.warning(f"⚠️ Pincode dataset missing at {file_path}. PIN resolution disabled.")
            self._dataset = {}
            self._loaded = True
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            if not isinstance(raw_data, list):
                logger.error("❌ Invalid dataset schema: pincodes.json must be a JSON array.")
                self._dataset = {}
                self._loaded = True
                return

            for entry in raw_data:
                if not isinstance(entry, dict):
                    continue
                    
                # Robust extraction handles both String and Integer JSON types safely
                pin = str(entry.get("pincode", "")).strip()
                if len(pin) == 6:
                    if pin not in self._dataset:
                        state_raw = str(entry.get("stateName", "")).strip().upper()
                        state_code = STATE_MAP_CONSTANT.get(state_raw, state_raw[:2])
                        
                        self._dataset[pin] = {
                            "district": str(entry.get("districtName", "")).strip().title(),
                            "state_code": state_code
                        }
                    
            logger.info(f"📍 Successfully loaded {len(self._dataset)} unique PIN codes into memory cache.")
            self._loaded = True
        except Exception as e:
            logger.error(f"❌ Failed to parse pincodes.json: {str(e)}")
            self._dataset = {}
            self._loaded = True

    def resolve(self, pincode: str) -> Optional[Dict[str, str]]:
        if not pincode:
            return None
        pin = pincode.strip()
        if len(pin) != 6:
            return None
        return self._dataset.get(pin)

pincode_resolver = PincodeResolver()