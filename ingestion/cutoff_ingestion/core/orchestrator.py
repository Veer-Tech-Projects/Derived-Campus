import logging
import requests
import re
import unicodedata
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
from sqlalchemy.orm import Session
from ingestion.common.services.governance import IngestionGovernanceController
from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalNotificationOrchestrator:
    def __init__(self, governance: IngestionGovernanceController):
        self.governance = governance

    def _make_fingerprint(self, text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize('NFD', text)
        text = re.sub(r'[\u200c\u200d\s\-\(\)\[\]\{\}\.,_\|]', '', text)
        return unicodedata.normalize('NFC', text).upper()

    def _normalize_text_for_parsing(self, text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize('NFC', text).upper()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def scan(self, db: Session, plugin: BaseCutoffPlugin, year: int) -> int:
        urls = plugin.get_seed_urls()
        target_url = urls.get(year)
        if not target_url: return 0

        logger.info(f"--- SCANNING {plugin.get_slug().upper()} ({year}) ---")
        headers = getattr(plugin, 'get_request_headers', lambda: {'User-Agent': 'Mozilla/5.0'})()

        try:
            response = requests.get(target_url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Network Failure: {e}")
            return 0

        soup = BeautifulSoup(response.content, 'html.parser')
        block_filters = plugin.get_notification_filters()
        
        pos_fps = {self._make_fingerprint(k) for k in block_filters['positive']}
        neg_fps = {self._make_fingerprint(k) for k in block_filters['negative']}
        child_negatives = [self._normalize_text_for_parsing(n) for n in plugin.get_child_filters()]
        
        new_count = 0
        processed_urls = set()

        # 1. FIND STRUCTURAL HEADERS
        # We explicitly EXCLUDE 'a' tags here. A PDF link is an Artifact, NOT a Notification Title.
        potential_headers = soup.find_all(['button', 'h5', 'strong', 'span', 'p', 'div'])

        for header in potential_headers:
            # Skip if this element is just a wrapper around a link we'll process later
            if header.find('a', href=True): 
                continue

            raw_text = header.get_text(" ", strip=True)
            if len(raw_text) < 5: continue

            # 2. DOUBLE GATE (Mandatory for Titles)
            header_fp = self._make_fingerprint(raw_text)
            has_positive = any(fp in header_fp for fp in pos_fps)
            has_negative = any(fp in header_fp for fp in neg_fps)

            if not has_positive or has_negative:
                continue

            # 3. ROUND DETECTION
            detected_round = plugin.normalize_round(self._normalize_text_for_parsing(raw_text))
            if detected_round is None:
                continue

            # 4. SCOPE RESOLUTION (Find the Container)
            scope_links = []
            
            # Strategy A: Bootstrap Accordion (Target ID)
            target_id = header.get('data-target') or header.get('aria-controls')
            if target_id:
                clean_id = target_id.replace('#', '')
                target_div = soup.find(id=clean_id)
                if target_div:
                    scope_links = target_div.find_all('a', href=True)

            # Strategy B: Sibling Scan (Legacy/Linear Layout)
            if not scope_links:
                # Look at next siblings until we hit another likely header or container
                curr = header.next_sibling
                while curr:
                    if isinstance(curr, Tag):
                        # Stop if we hit another header-like element
                        if curr.name in ['h5', 'button', 'h4', 'h3']: 
                            break
                        scope_links.extend(curr.find_all('a', href=True))
                        # If the tag itself is a link, add it
                        if curr.name == 'a' and curr.has_attr('href'):
                            scope_links.append(curr)
                    curr = curr.next_sibling

            # 5. PROCESS LINKS IN SCOPE
            for link in scope_links:
                full_url = urljoin(target_url, link['href'])
                
                # Basic Guard
                if not full_url.lower().endswith('.pdf'): continue
                if full_url in processed_urls: continue

                link_text = link.get_text(" ", strip=True)
                norm_link = self._normalize_text_for_parsing(link_text)

                # NEGATIVE FILTER ONLY (User Requirement)
                # We do NOT check for positive keywords here. Inheritance is trusted.
                if any(neg in norm_link for neg in child_negatives):
                    continue

                processed_urls.add(full_url)
                
                # Standardize Name
                clean_name, original_name, is_standardized = plugin.normalize_artifact_name(link_text)

                metadata = {
                    "year": year,
                    "round_name": clean_name,
                    "original_name": original_name,
                    "is_standardized": is_standardized,
                    "round": detected_round,
                    "seat_type": None,
                    "exam_slug": plugin.get_slug()
                }

                try:
                    self.governance.register_discovery(
                        db=db, pdf_path=full_url, notification_url=target_url,
                        metadata=metadata, detection_reason="ScopedContextDiscovery",
                        source="PDF_LINK"
                    )
                    db.commit()
                    new_count += 1
                except:
                    db.rollback()

        logger.info(f"[{year}] Final Ingestion: {new_count} unique artifacts.")
        return new_count