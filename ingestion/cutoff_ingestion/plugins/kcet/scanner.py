import logging
import re
import unicodedata
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from typing import List
from ingestion.cutoff_ingestion.core.base_scanner import BaseScanner, ScannedArtifact

logger = logging.getLogger(__name__)

class KCETScanner(BaseScanner):
    def __init__(self, plugin):
        self.plugin = plugin
        filters = plugin.get_notification_filters()
        # Pre-compute fingerprints for speed
        self.pos_fps = {self._make_fingerprint(k) for k in filters.get('positive', [])}
        self.neg_fps = {self._make_fingerprint(k) for k in filters.get('negative', [])}
        self.child_negatives = [self._normalize_text(n) for n in plugin.get_child_filters()]

    def _make_fingerprint(self, text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize('NFD', text)
        text = re.sub(r'[\u200c\u200d\s\-\(\)\[\]\{\}\.,_\|]', '', text)
        return unicodedata.normalize('NFC', text).upper()

    def _normalize_text(self, text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize('NFC', text).upper()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_artifacts(self, html_content: bytes, base_url: str) -> List[ScannedArtifact]:
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        processed_urls = set()

        # 1. FIND STRUCTURAL HEADERS (Accordion/Sibling Strategy)
        potential_headers = soup.find_all(['button', 'h5', 'strong', 'span', 'p', 'div'])

        for header in potential_headers:
            if header.find('a', href=True): continue

            raw_text = header.get_text(" ", strip=True)
            if len(raw_text) < 5: continue

            # 2. DOUBLE GATE (Mandatory for Titles)
            header_fp = self._make_fingerprint(raw_text)
            has_positive = any(fp in header_fp for fp in self.pos_fps)
            has_negative = any(fp in header_fp for fp in self.neg_fps)

            # Strict Gate: Must match Positive AND NOT match Negative
            if not has_positive or has_negative:
                continue

            # 3. STRICT ROUND DETECTION
            norm_header = self._normalize_text(raw_text)
            detected_round = self.plugin.normalize_round(norm_header)
            
            if detected_round is None:
                continue # [STRICT] No round -> No access.

            # 4. SCOPE RESOLUTION
            scope_links = []
            
            # Strategy A: Bootstrap Accordion
            target_id = header.get('data-target') or header.get('aria-controls')
            if target_id:
                clean_id = target_id.replace('#', '')
                target_div = soup.find(id=clean_id)
                if target_div:
                    scope_links = target_div.find_all('a', href=True)

            # Strategy B: Sibling Scan
            if not scope_links:
                curr = header.next_sibling
                while curr:
                    if isinstance(curr, Tag):
                        if curr.name in ['h5', 'button', 'h4', 'h3']: break
                        scope_links.extend(curr.find_all('a', href=True))
                        if curr.name == 'a' and curr.has_attr('href'):
                            scope_links.append(curr)
                    curr = curr.next_sibling

            # 5. PROCESS LINKS
            for link in scope_links:
                href = link.get('href')
                if not href: continue
                
                full_url = urljoin(base_url, href)
                
                if not full_url.lower().endswith('.pdf'): continue
                if full_url in processed_urls: continue

                link_text = link.get_text(" ", strip=True)
                norm_link_text = self._normalize_text(link_text)

                # NEGATIVE FILTER (On the child link itself)
                if any(neg in norm_link_text for neg in self.child_negatives):
                    continue

                processed_urls.add(full_url)
                
                results.append(ScannedArtifact(
                    url=full_url,
                    link_text=link_text,
                    context_header=raw_text,
                    detected_round=detected_round,
                    detection_method="ContextMatch"
                ))

        return results