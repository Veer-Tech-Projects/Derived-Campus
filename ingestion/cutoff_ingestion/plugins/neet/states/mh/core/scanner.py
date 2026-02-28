import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List

from ingestion.cutoff_ingestion.core.base_scanner import BaseScanner, ScannedArtifact
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core import constants as M

logger = logging.getLogger(__name__)

class MHNeetScanner(BaseScanner):
    def extract_artifacts(self, html_content: bytes, base_url: str) -> List[ScannedArtifact]:
        soup = BeautifulSoup(html_content, 'html.parser')
        artifacts = []
        seen_urls = set()

        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href')
            
            # S3 URL safety: Strip query parameters before checking extension
            if not href.lower().split('?')[0].endswith('.pdf'):
                continue

            full_url = urljoin(base_url, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Extract Text (Link + Parent Fallback for short links like "New")
            raw_text = link.get_text(" ", strip=True)
            if len(raw_text) < 10 and link.parent:
                raw_text = link.parent.get_text(" ", strip=True)
            
            norm_text = raw_text.upper()

            # --- OPTIMIZED GATES ---
            
            # GATE 1: Strict Whitelist (Fast Fail) - Must explicitly be a Selection List
            if not M.P_TARGET_SELECTION.search(norm_text):
                continue

            # GATE 2: Noise Filter (Evaluated only if it looks like a target)
            if M.P_BLOCK_IGNORED.search(norm_text):
                continue

            # EXTRACT ROUND SEQUENCE 
            # WARNING: Uses shared M.P_ROUND_SEQ to stay perfectly synced with base_mh_neet_plugin.py
            round_seq = 0
            seq_match = M.P_ROUND_SEQ.search(norm_text)
            if seq_match:
                r_str = seq_match.group(1).strip()
                if r_str in M.ROUND_MAP:
                    round_seq = M.ROUND_MAP[r_str]
                else:
                    try:
                        round_seq = int(r_str)
                    except ValueError:
                        round_seq = 0
            
            # THE LOGGING RULE: Capture missing sequence anomalies
            if round_seq == 0:
                logger.warning(f"Anomaly: Missing sequence for Selection List, defaulting to 0. Text: '{norm_text}'")

            artifacts.append(ScannedArtifact(
                url=full_url,
                link_text=raw_text,
                context_header="MH_NEET_SELECTION_LIST",
                detected_round=round_seq,
                detection_method="SemanticClassifier"
            ))

        return artifacts