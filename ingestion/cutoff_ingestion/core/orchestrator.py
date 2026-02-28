import logging
import requests
import hashlib
import time
import os
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func
from ingestion.common.services.governance import IngestionGovernanceController
from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin
from app.models import DiscoveredArtifact

# [SECURITY] Configurable Verification
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() == "true"
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalNotificationOrchestrator:
    def __init__(self, governance: IngestionGovernanceController):
        self.governance = governance
        self.request_timeout = 30
        
        # --- ENTERPRISE RESILIENCE: Connection Pooling & Retries ---
        self.session = requests.Session()
        retries = Retry(
            total=3,                # Try 3 times
            backoff_factor=1,       # Wait 1s, 2s, 4s...
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _get_remote_fingerprint(self, url: str, headers: dict) -> tuple[bool, str, int]:
        """
        Robust 'Head Check' with Range GET Fallback.
        """
        try:
            # 1. Attempt HEAD
            resp = self.session.head(url, headers=headers, timeout=self.request_timeout, allow_redirects=True, verify=VERIFY_SSL)
            
            # 2. Gov server blocked HEAD? Try Streamed GET.
            if resp.status_code >= 400:
                resp = self.session.get(url, headers=headers, stream=True, timeout=self.request_timeout, verify=VERIFY_SSL)
                resp.close() 

            if resp.status_code >= 400: 
                return False, None, 0

            # 3. Hashing Strategy (Ironclad)
            etag = resp.headers.get('ETag', '').strip('"')
            
            if not etag:
                lm = resp.headers.get('Last-Modified')
                cl = resp.headers.get('Content-Length')
                
                if lm or cl:
                    # Synthetic Hash from Metadata
                    etag = hashlib.md5(f"{lm}{cl}".encode()).hexdigest()
                else:
                    # [RANGE GET FALLBACK]
                    # If metadata is missing, download first 4KB to fingerprint content.
                    try:
                        range_header = headers.copy()
                        range_header["Range"] = "bytes=0-4096"
                        partial_resp = self.session.get(url, headers=range_header, timeout=10, verify=VERIFY_SSL)
                        if partial_resp.status_code in [200, 206]:
                            etag = hashlib.md5(partial_resp.content).hexdigest()
                        else:
                            # Total desperation fallback
                            etag = hashlib.md5(url.encode()).hexdigest()
                    except:
                        etag = hashlib.md5(url.encode()).hexdigest()
            
            size = int(resp.headers.get('Content-Length', 0))
            return True, etag, size

        except Exception as e:
            logger.warning(f"Liveness Check Failed: {url} - {e}")
            return False, None, 0

    def scan(self, db: Session, plugin: BaseCutoffPlugin, year: int) -> int:
        urls = plugin.get_seed_urls()
        target_url = urls.get(year)
        if not target_url: return 0

        logger.info(f"--- SCANNING {plugin.get_slug().upper()} ({year}) ---\nSource: {target_url}")
        
        headers = getattr(plugin, 'get_request_headers', lambda: {'User-Agent': 'DerivedBot/1.0'})()
        
        # 1. Fetch Seed Page
        try:
            response = self.session.get(target_url, headers=headers, timeout=self.request_timeout, verify=VERIFY_SSL)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch seed page: {e}")
            return 0

        # 2. DELEGATE TO SCANNER STRATEGY
        scanner = plugin.get_scanner()
        artifacts = scanner.extract_artifacts(response.content, target_url)
        
        # --- OBSERVABILITY METRICS ---
        metrics = {"found": len(artifacts), "new": 0, "updated": 0, "failed": 0, "skipped_dead": 0}
        logger.info(f"Scanner identified {metrics['found']} valid candidates.")

        # 3. PROCESS LOOP
        for item in artifacts:
            # Check DB (Read - Fast)
            existing_artifact = db.execute(
                select(DiscoveredArtifact).where(
                    DiscoveredArtifact.exam_code == plugin.get_slug(),
                    DiscoveredArtifact.year == year,
                    DiscoveredArtifact.pdf_path == item.url
                )
            ).scalar_one_or_none()

            # [EFFICIENCY] Politeness Delay only before Network Calls
            time.sleep(plugin.get_politeness_delay())

            # Liveness Check (Network - Slow)
            is_live, remote_hash, size = self._get_remote_fingerprint(item.url, headers)
            if not is_live: 
                metrics["skipped_dead"] += 1
                continue 

            # DB Operations (Write)
            try:
                if existing_artifact:
                    existing_artifact.last_seen_at = func.now()
                    
                    if existing_artifact.content_hash is None:
                        existing_artifact.content_hash = remote_hash
                        db.commit()
                        metrics["updated"] += 1
                        continue
                    
                    if existing_artifact.content_hash != remote_hash:
                        logger.warning(f"⚠️ Silent Revision: {item.url}")
                        existing_artifact.previous_content_hash = existing_artifact.content_hash
                        existing_artifact.content_hash = remote_hash
                        if existing_artifact.status != "PENDING":
                            existing_artifact.status = "PENDING"
                            existing_artifact.review_notes = f"Auto-Reset. Size: {size}b"
                        db.commit()
                        metrics["updated"] += 1
                    else:
                        db.commit()
                else:
                    clean_name, original_name, is_standardized = plugin.normalize_artifact_name(item.link_text)
                    
                    metadata = {
                        "year": year,
                        "round_name": clean_name,
                        "original_name": original_name,
                        "is_standardized": is_standardized,
                        "round": item.detected_round, 
                        "seat_type": None, 
                        "exam_slug": plugin.get_slug(),
                        "detection_method": item.detection_method,
                        "context_header": item.context_header
                    }

                    art_id = self.governance.register_discovery(
                        db=db, pdf_path=item.url, notification_url=target_url,
                        metadata=metadata, detection_reason=f"Scanner:{item.detection_method}",
                        source="PDF_LINK"
                    )
                    db.execute(
                        update(DiscoveredArtifact)
                        .where(DiscoveredArtifact.id == art_id)
                        .values(content_hash=remote_hash)
                    )
                    db.commit()
                    metrics["new"] += 1
                    logger.info(f"✅ Discovered: {clean_name} (Round: {item.detected_round})")
                    
            except Exception as e:
                db.rollback()
                metrics["failed"] += 1
                logger.error(f"Transaction failed for {item.url}: {e}")

        logger.info(f"[{year}] Run Complete. Metrics: {metrics}")
        return metrics["new"]