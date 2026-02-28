import re
import json
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from ingestion.cutoff_ingestion.core.base_scanner import BaseScanner, ScannedArtifact
from ingestion.cutoff_ingestion.plugins.mhtcet.core import constants as M

logger = logging.getLogger(__name__)

class MHTCETScanner(BaseScanner):
    
    def extract_artifacts(self, html_content: bytes, base_url: str) -> list[ScannedArtifact]:
        soup = BeautifulSoup(html_content, 'html.parser')
        artifacts = []
        seen_urls = set()

        # 1. Target ALL anchors on the page
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href')
            
            # 2. ASP.NET Filter: Ignore all links except the dynamic document viewer
            if "ViewPublicDocument.aspx" not in href:
                continue

            full_url = urljoin(base_url, href)
            if full_url in seen_urls:
                continue

            # 3. Text Extraction (Penetrates <lang> tags)
            raw_text = link.get_text(" ", strip=True)
            norm_text = self._normalize_text(raw_text)

           # 4. Anti-Pollution Gates (Positive First, Negative Second)
            
            # GATE 1: MUST contain "ROUND" and "CUTOFF"
            if not (M.P_ROUND.search(norm_text) and M.P_CUTOFF.search(norm_text)):
                continue

            # GATE 2: MUST NOT contain blocklist words (Brochure, Merit, etc.)
            if M.P_BLOCK.search(norm_text):
                continue

            # 5. Extraction & Structuring
            r_num, r_label = self._extract_round(norm_text)
            if r_num == 0: 
                continue

            quota, seat_type = self._extract_quota_and_type(norm_text)
            if not quota and seat_type != "DIPLOMA":
                logger.warning(f"MHTCET Scanner dropped unknown quota/type for text: {raw_text}")
                continue

            seen_urls.add(full_url)

            # 6. Metadata Injection
            # Self-contained payload for Phase 2 decoupling
            context_payload = json.dumps({
                "quota": quota,
                "seat_type": seat_type,
                "normalized_round_label": r_label,
                "round": r_num
            })

            artifacts.append(ScannedArtifact(
                url=full_url,
                link_text=raw_text, # Preserved for deterministic slug generation
                context_header=context_payload, 
                detected_round=r_num,
                detection_method="ASP_NET_Viewer_Extractor"
            ))

        return artifacts

    def _normalize_text(self, text: str) -> str:
        """Sanitizes spacing, hyphens, and standardizes Cutoff nomenclature."""
        t = text.upper()
        t = t.replace("NEW", "")
        # Normalizes Unicode en-dashes, em-dashes, and standard hyphens
        t = re.sub(r'[-‐-‒–—―_]+', ' ', t) 
        t = re.sub(r'\s+', ' ', t).strip() 
        t = t.replace("CUT OFF", "CUTOFF") 
        return t

    def _extract_round(self, text: str) -> tuple[int, str]:
        match = M.P_ROUND.search(text)
        if not match: return 0, ""
        
        r_str = match.group(1).strip()
        
        # Strict Integer Type Enforcement
        if r_str in M.ROUND_MAP:
            r_int = M.ROUND_MAP[r_str]
        else:
            try:
                r_int = int(r_str)
            except ValueError:
                return 0, ""
                
        return r_int, f"R{r_int}"

    def _extract_quota_and_type(self, text: str) -> tuple[str, str]:
        """Returns (Quota, Seat_Type). Uses strict word boundaries."""
        if "DIPLOMA" in text:
            return None, "DIPLOMA"
            
        # [FIX] AI is more specific than MH. Always check it first!
        if re.search(r'\bAI\b', text) or "ALL INDIA" in text:
            return "AI", "REGULAR"
        if re.search(r'\bMH\b', text) or "MAHARASHTRA" in text:
            return "MH", "REGULAR"
            
        return None, "UNKNOWN"