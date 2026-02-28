from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
import logging

from ingestion.cutoff_ingestion.core.base_scanner import BaseScanner, ScannedArtifact
from ingestion.cutoff_ingestion.plugins.neet.states.ka import constants as K

logger = logging.getLogger(__name__)

class KarnatakaNEETScanner(BaseScanner):
    
    def __init__(self, plugin):
        self.plugin = plugin

    def extract_artifacts(self, html_content: bytes, base_url: str) -> List[ScannedArtifact]:
        """
        Architectural Pivot: Link-Centric Scanning.
        We scan ALL PDF links globally to ignore DOM structural drift.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        artifacts = []
        seen_urls = set()

        # 1. FIND ALL PDF LINKS (Zero DOM Bias)
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href')
            full_url = urljoin(base_url, href)

            # A. PRE-FILTER: PDF Only & Dedupe
            if full_url in seen_urls: continue
            if not full_url.lower().endswith('.pdf'): continue

            # B. CONTEXT EXTRACTION (The Smart Layer)
            link_text = link.get_text(" ", strip=True).upper()
            parent_text = link.parent.get_text(" ", strip=True).upper() if link.parent else ""
            
            # [CRITICAL FIX] Find header with increased depth (5 levels)
            header_text = self._find_nearest_header(link)
            
            # Combine signals: Header -> Parent -> Link
            combined_text = f"{header_text} | {parent_text} | {link_text}"

            # --- GATES ---

            # Gate 1: Hard Trash (Finance/Admin)
            if any(p.search(combined_text) for p in K.HARD_TRASH):
                continue

            # Gate 2: Semantic Validation (Inheritance Logic)
            # The Semantic (Allotment/Cutoff) can be in the Link OR the Header.
            # Example: Header="Round 2 Allotment", Link="Medical" -> VALID.
            is_semantic_valid = K.P_ALLOT.search(combined_text) or K.P_CUTOFF.search(combined_text)
            if not is_semantic_valid:
                continue

            # Gate 3: Soft Trash (Provisional/Schedule)
            if any(p.search(combined_text) for p in K.SOFT_TRASH):
                continue

            # Gate 4: Round Detection (Inherited from Header)
            r_num = self._detect_round(combined_text)
            if r_num == 0: continue

            # Gate 5: Context Authority
            has_context = (
                K.P_UGNEET.search(combined_text) or 
                K.P_UGCET.search(combined_text) or
                K.P_UGAYUSH.search(combined_text) or
                K.P_UGDENTAL.search(combined_text)
            )
            
            if not has_context:
                # Weak Context Check (Medical/Dental keywords without UGNEET prefix)
                if not (K.P_MEDICAL.search(combined_text) or 
                        K.P_DENTAL.search(combined_text) or 
                        K.P_AYUSH.search(combined_text)):
                    continue

            # SUCCESS
            seen_urls.add(full_url)
            artifacts.append(ScannedArtifact(
                url=full_url,
                link_text=link_text,
                context_header=header_text[:150], 
                detected_round=r_num,
                detection_method="KEA_Link_Centric_Deep"
            ))

        return artifacts

    def _find_nearest_header(self, element) -> str:
        """
        Walks up the DOM tree to find the nearest semantic header.
        Depth increased to 5 to handle: Link -> Span -> P -> Body -> Collapse -> Header
        """
        curr = element
        # [CRITICAL FIX] Increased depth from 3 to 5
        for _ in range(5):
            if not curr: break
            
            # 1. Previous Sibling Tag (Standard)
            prev = curr.find_previous_sibling(['h4', 'h5', 'h6', 'strong', 'thead', 'b'])
            if prev: return prev.get_text(" ", strip=True).upper()

            # 2. Previous Sibling Class (For Accordions)
            # div.card-header is often a sibling of div.collapse
            prev_class = curr.find_previous_sibling(class_=K.P_HEADER_CLASS)
            if prev_class: return prev_class.get_text(" ", strip=True).upper()

            # 3. Parent Class (Standard)
            if curr.parent:
                classes = curr.parent.get('class', [])
                if isinstance(classes, str): classes = [classes]
                if classes and any(K.P_HEADER_CLASS.search(c) for c in classes):
                    return curr.parent.get_text(" ", strip=True).upper()

            curr = curr.parent
            
        return ""

    def _detect_round(self, text: str) -> int:
        if K.P_SPECIAL.search(text) and K.P_STRAY.search(text): return 5 
        if K.P_STRAY.search(text): return 4
        if K.P_MOPUP.search(text): return 3
        if K.P_ROUND_3.search(text): return 3
        if K.P_ROUND_2.search(text): return 2
        if K.P_ROUND_1.search(text): return 1
        return 0