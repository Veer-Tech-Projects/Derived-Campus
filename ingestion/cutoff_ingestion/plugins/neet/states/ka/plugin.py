from typing import Dict, List, Optional, Any
from ingestion.cutoff_ingestion.plugins.neet.core.base_state_plugin import BaseNEETStatePlugin
from ingestion.cutoff_ingestion.plugins.neet.states.ka.scanner import KarnatakaNEETScanner
from ingestion.cutoff_ingestion.plugins.neet.states.ka.adapter import KarnatakaNEETContextAdapter
from ingestion.cutoff_ingestion.plugins.neet.states.ka.table_parser import KarnatakaNEETTableParser
from ingestion.cutoff_ingestion.plugins.neet.states.ka.row_standardizer import KarnatakaNEETRowStandardizer

class KarnatakaNEETPlugin(BaseNEETStatePlugin):
    
    def get_slug(self) -> str:
        return "neet_ka"

    def get_scanner(self):
        return KarnatakaNEETScanner(self)

    def get_seed_urls(self) -> Dict[int, str]:
        # Verified KEA Annual Archives
        return {
            2026: "https://cetonline.karnataka.gov.in/kea/ugneet2026",
            2025: "https://cetonline.karnataka.gov.in/kea/ugneet2025",
            2024: "https://cetonline.karnataka.gov.in/kea/ugneet24",
            2023: "https://cetonline.karnataka.gov.in/kea/Neet2023"
        }

    # --- PARSING & ADAPTER HOOKS ---

    def get_adapter(self) -> Any:
        return KarnatakaNEETContextAdapter()

    def get_parser(self, pdf_path: str) -> Any:
        raise NotImplementedError("Use get_parser_with_context to inject artifact state.")

    def get_parser_with_context(self, pdf_path: str, artifact: Any) -> Any:
        # Passes the dynamic Round Number and UUID into the parser for validation
        return KarnatakaNEETTableParser(pdf_path, artifact.id, artifact.round_number)

    def sanitize_round_name(self, raw_name: str) -> str:
        return raw_name

    def transform_row_to_context(self, row: Dict[str, Any], artifact: Any, sanitized_stream: str) -> Dict[str, Any]:
        """
        The Bridge between the Raw Parser and the Strict Adapter.
        """
        clean_kea_code = KarnatakaNEETRowStandardizer.extract_kea_code(row['kea_code_raw'])
        course, seat = KarnatakaNEETRowStandardizer.parse_course_string(row['course_name_raw'])
        loc_type = KarnatakaNEETRowStandardizer.resolve_location_type(row['category_raw'])

        return {
            "college_name_raw": row['college_name_raw'],
            "source_type": "neet_ka_pdf",
            "course_normalized": course,
            "seat_type_normalized": seat,
            "location_type_normalized": loc_type,
            "category_raw": row['category_raw'],
            "year": artifact.year,
            "round": artifact.round_number,
            "kea_code": clean_kea_code or row['kea_code_raw'],
            "course_name_raw": row['course_name_raw'],
            "source_artifact_id": row['source_artifact_id']
        }