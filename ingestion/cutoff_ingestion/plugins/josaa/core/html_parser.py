import logging
from bs4 import BeautifulSoup
from typing import Iterator, Dict, Any

logger = logging.getLogger(__name__)

class JosaaGridParser:
    """
    Pure HTML Grid Extractor utilizing C-backed lxml for massive 14MB+ files.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> Iterator[Dict[str, Any]]:
        logger.info(f"Parsing HTML Grid from: {self.file_path}")
        with open(self.file_path, 'rb') as f:
            soup = BeautifulSoup(f.read(), 'lxml')
        
        table = soup.find('table', id='ctl00_ContentPlaceHolder1_GridView1')
        if not table:
            logger.error("Target GridView1 not found in HTML. Stream may be corrupted.")
            return

        headers = []
        for tr in table.find_all('tr'):
            # Dynamic column mapping (Zero Hardcoding)
            if not headers:
                th_elements = tr.find_all('th')
                if th_elements:
                    headers = [th.get_text(separator=" ", strip=True) for th in th_elements]
                continue
            
            td_elements = tr.find_all('td')
            if not td_elements or len(td_elements) != len(headers):
                continue
            
            row_data = {}
            for i, td in enumerate(td_elements):
                row_data[headers[i]] = td.get_text(separator=" ", strip=True)
            
            # --- MANDATORY DTO MAPPINGS FOR UNIVERSAL ENGINE ---
            row_data["college_name_raw"] = row_data.get("Institute", "")
            row_data["cutoff_rank"] = row_data.get("Closing Rank", "0")
            
            yield row_data