from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .constants import REQUIRED_TOKENS

class StateExtractionError(Exception):
    """Raised when the DOM violates expected state matrix rules."""
    pass

@dataclass(frozen=True)
class SelectNode:
    control_id: str
    current_value: str
    available_options: List[str]
    requires_postback: bool

class StateExtractor:
    """
    Pure deterministic DOM parser. Zero IO.
    Enforces foundational cryptographic state invariants.
    """
    @staticmethod
    def extract_state(html_bytes: bytes) -> Tuple[Dict[str, str], List[SelectNode]]:
        soup = BeautifulSoup(html_bytes, 'lxml')
        form_state: Dict[str, str] = {}
        select_queue: List[SelectNode] = []

        def _safe_add(name: str, value: str):
            if name in form_state:
                raise StateExtractionError(f"Duplicate form key detected: {name}. Potential DOM corruption.")
            form_state[name] = value

        # 1. Extract <input> tags
        for input_tag in soup.find_all('input'):
            if input_tag.has_attr('disabled'): continue  # [FORENSIC FIX]: Ignore disabled
            name = input_tag.get('name')
            if not name: continue
            
            type_ = input_tag.get('type', '').lower()
            if type_ in ('submit', 'button', 'image', 'reset'): continue
            if type_ in ('checkbox', 'radio') and not input_tag.has_attr('checked'): continue
            
            _safe_add(name, input_tag.get('value', ''))

        # 2. Extract <textarea> tags
        for textarea_tag in soup.find_all('textarea'):
            if textarea_tag.has_attr('disabled'): continue  # [FORENSIC FIX]
            name = textarea_tag.get('name')
            if not name: continue
            _safe_add(name, textarea_tag.text or '')

        # 3. Extract <select> tags
        for select_tag in soup.find_all('select'):
            if select_tag.has_attr('disabled'): continue
            name = select_tag.get('name')
            if not name: continue

            options = []
            for opt in select_tag.find_all('option'):
                val = opt.get('value')
                if val is not None:
                    options.append(val)

            # [CRITICAL FIX]: Empty dropdowns are not successful HTML controls.
            # Sending them triggers ASP.NET EventValidation tampering exceptions.
            if not options:
                continue

            selected_option = select_tag.find('option', selected=True)
            current_value = selected_option.get('value', '') if selected_option else (options[0] if options else '')

            _safe_add(name, current_value)

            onchange_attr = select_tag.get('onchange', '')
            select_queue.append(SelectNode(
                control_id=name,
                current_value=current_value,
                available_options=options,
                requires_postback='__doPostBack' in onchange_attr
            ))

        missing = REQUIRED_TOKENS - form_state.keys()
        if missing:
            raise StateExtractionError(f"Missing required ASP.NET tokens: {missing}")

        return form_state, select_queue