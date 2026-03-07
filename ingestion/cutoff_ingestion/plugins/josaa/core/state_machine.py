import time
import random
import logging
import httpx
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .constants import *
from .state_extractor import StateExtractor, StateExtractionError
from .network_client import JosaaNetworkClient

logger = logging.getLogger(__name__)

class StateIntegrityError(Exception): pass

class JosaaStateMachine:
    def __init__(self, target_url: str, target_year: int):
        self.target_url = target_url
        self.target_year = target_year

    def _verify_status(self, response: httpx.Response, state_id: str):
        if response.status_code != 200:
            location = response.headers.get("Location", "Unknown")
            set_cookie = response.headers.get("Set-Cookie", "None")
            raise StateIntegrityError(
                f"[{state_id}] HTTP {response.status_code}. Request rejected. "
                f"Redirect Location: {location} | Set-Cookie: {set_cookie}"
            )

    def _check_for_errors(self, html_bytes: bytes, state_id: str):
        chunk = html_bytes[:STREAM_CHUNK_SIZE].decode('utf-8', errors='ignore')
        for pattern in KNOWN_ASPNET_ERRORS:
            if pattern.search(chunk):
                raise StateIntegrityError(f"[{state_id}] Server Error Signature Detected: {pattern.pattern}")

    def discover_rounds(self) -> List[int]:
        with JosaaNetworkClient() as client:
            resp = client.get(self.target_url)
            self._verify_status(resp, "S0_DISCOVERY")
            self._check_for_errors(resp.content, "S0_DISCOVERY")
            
            form_state, select_queue = StateExtractor.extract_state(resp.content)

            # --- [HARDENED FIX]: Archive Page Pre-Flight (Select Year First) ---
            for node in select_queue:
                if not node.requires_postback:
                    continue
                
                target_year_str = str(self.target_year)
                if target_year_str in node.available_options:
                    numeric_options = [opt for opt in node.available_options if opt.isdigit()]
                    
                    if len(numeric_options) >= 2:
                        logger.info(f"Detected Year Dropdown: {node.control_id}. Executing Pre-Flight POST...")
                        payload = form_state.copy()
                        payload[TOKEN_EVENTTARGET] = node.control_id
                        payload[TOKEN_EVENTARGUMENT] = ""
                        payload[node.control_id] = target_year_str
                        
                        post_resp = client.post(self.target_url, data=payload)
                        self._verify_status(post_resp, "S0_YEAR_SELECT")
                        self._check_for_errors(post_resp.content, "S0_YEAR_SELECT")
                        
                        # [CRITICAL FIX]: Synchronize global state
                        form_state, select_queue = StateExtractor.extract_state(post_resp.content)
                        break  

            # --- Structural Round Discovery ---
            for node in select_queue:
                valid_ints = []
                for opt in node.available_options:
                    if opt in ["0", "", "-1", "ALL"] or "select" in opt.lower():
                        continue
                    try:
                        val = int(opt)
                        if val > 0: valid_ints.append(val)
                    except ValueError:
                        pass

                if valid_ints:
                    valid_ints = sorted(list(set(valid_ints)))
                    if valid_ints == list(range(1, len(valid_ints) + 1)):
                        if len(valid_ints) <= 15:
                            return valid_ints
        return []

    @retry(
        stop=stop_after_attempt(MAX_RETRIES_PER_ROUND),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        retry=retry_if_exception_type((StateIntegrityError, StateExtractionError, httpx.RequestError)),
        reraise=True
    )
    def execute_round(self, target_round: int, temp_filepath: str) -> bool:
        logger.info(f"Initiating Cascade for Round {target_round}...")

        with JosaaNetworkClient() as client:
            # === State S0: Bootstrap ===
            resp = client.get(self.target_url)
            self._verify_status(resp, "S0_GET")
            self._check_for_errors(resp.content, "S0_GET")
            form_state, select_queue = StateExtractor.extract_state(resp.content)

            # === State S1..SN: Autonomous Dynamic Cascade ===
            processed_controls = set()
            
            while True:
                target_node = None
                for node in select_queue:
                    if node.requires_postback and node.control_id not in processed_controls:
                        target_node = node
                        break
                
                if not target_node:
                    break 
                
                payload = form_state.copy()
                payload[TOKEN_EVENTTARGET] = target_node.control_id
                payload[TOKEN_EVENTARGUMENT] = ""

                target_round_str = str(target_round)
                target_year_str = str(self.target_year)

                if target_year_str in target_node.available_options:
                    payload[target_node.control_id] = target_year_str
                elif target_round_str in target_node.available_options:
                    payload[target_node.control_id] = target_round_str
                elif TARGET_VALUE_ALL in target_node.available_options:
                    payload[target_node.control_id] = TARGET_VALUE_ALL
                else:
                    payload[target_node.control_id] = target_node.available_options[-1]

                time.sleep(random.uniform(JITTER_MIN_SEC, JITTER_MAX_SEC))
                logger.info(f"Triggering AutoPostBack for: {target_node.control_id}")
                
                post_resp = client.post(self.target_url, data=payload)
                self._verify_status(post_resp, f"SN_{target_node.control_id}")
                self._check_for_errors(post_resp.content, f"SN_{target_node.control_id}")

                new_state, new_queue = StateExtractor.extract_state(post_resp.content)
                
                if new_state[TOKEN_VIEWSTATE] == form_state[TOKEN_VIEWSTATE]:
                    raise StateIntegrityError(f"[{target_node.control_id}] ViewState failed to mutate. Cascade corrupted.")

                form_state = new_state
                select_queue = new_queue
                processed_controls.add(target_node.control_id)

            # === State SF: Final Submit ===
            payload = form_state.copy()
            payload[TOKEN_EVENTTARGET] = ""
            payload[TOKEN_EVENTARGUMENT] = ""

            # [CRITICAL FIX]: Inject values for non-postback dropdowns
            for node in select_queue:
                if node.control_id not in processed_controls:
                    target_round_str = str(target_round)
                    target_year_str = str(self.target_year)

                    if target_year_str in node.available_options:
                        payload[node.control_id] = target_year_str
                    elif target_round_str in node.available_options:
                        payload[node.control_id] = target_round_str
                    elif TARGET_VALUE_ALL in node.available_options:
                        payload[node.control_id] = TARGET_VALUE_ALL
                    elif node.available_options:
                        payload[node.control_id] = node.available_options[-1]

            payload[BTN_SUBMIT_NAME] = BTN_SUBMIT_VALUE

            with client.stream_post(self.target_url, data=payload) as stream_resp:
                self._verify_status(stream_resp, "SF_SUBMIT")
                iterator = stream_resp.iter_bytes(chunk_size=STREAM_CHUNK_SIZE)
                
                buffer = b""
                buffer_lower = b""
                grid_found = False
                
                for chunk in iterator:
                    buffer += chunk
                    buffer_lower += chunk.lower()
                    
                    if b"<table" in buffer_lower and b"<th" in buffer_lower:
                        grid_found = True
                        break
                    if len(buffer) > MAX_GRID_PROBE_BYTES:
                        break

                if not grid_found:
                    raise StateIntegrityError("[VF] Structural Table/Grid Data not found in response stream.")

                with open(temp_filepath, 'wb') as f:
                    f.write(buffer)
                    for chunk in iterator:
                        f.write(chunk)

        return True