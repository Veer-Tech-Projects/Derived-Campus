import os
import hashlib
import logging
from typing import List, Optional
from ingestion.cutoff_ingestion.core.base_scanner import BaseScanner, ScannedArtifact
from .state_machine import JosaaStateMachine

logger = logging.getLogger(__name__)

class JosaaScanner(BaseScanner):
    def __init__(self, temp_dir="/src/temp_downloads"):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_artifacts(self, html_content: bytes, base_url: str, year: Optional[int] = None) -> List[ScannedArtifact]:
        # [DEFENSIVE FIX]: Fail fast to prevent silent data drift
        if year is None:
            raise ValueError("JoSAA scanner requires an explicit year context to operate.")
            
        machine = JosaaStateMachine(base_url, year)
        
        try:
            available_rounds = machine.discover_rounds()
            logger.info(f"Discovered {len(available_rounds)} available rounds at {base_url} for Year {year}")
        except Exception as e:
            # [ENTERPRISE FIX]: Fail loud. Do not swallow exceptions into an empty list.
            logger.error(f"FATAL: Failed to bootstrap round discovery. Propagating exception: {e}")
            raise

        artifacts = []
        for r in available_rounds:
            url_hash = hashlib.sha256(base_url.encode()).hexdigest()[:8]
            filepath = os.path.join(self.temp_dir, f"josaa_r{r}_{url_hash}.html")
            
            try:
                success = machine.execute_round(r, filepath)
                if success:
                    artifacts.append(ScannedArtifact(
                        url=filepath, 
                        link_text=f"Round {r} Cutoff (HTML)",
                        context_header="JoSAA Final Ranks",
                        detected_round=r,
                        detection_method="Active_State_Emulation"
                    ))
            except Exception as e:
                # We log and continue here to salvage other rounds if a single round's grid times out
                logger.error(f"Round {r} Extraction Failed completely after max retries: {e}")

        return artifacts