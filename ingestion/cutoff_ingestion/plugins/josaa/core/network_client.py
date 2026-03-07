import httpx
from typing import Dict

class JosaaNetworkClient:
    """
    Pure IO Layer. Manages session cookies exclusively for a single round's lifecycle.
    Limits connections to prevent socket exhaustion.
    """
    def __init__(self, timeout: int = 45):
        self.client = httpx.Client(
            http2=False,
            follow_redirects=False,  # DO NOT CHANGE THIS YET
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Origin": "https://josaa.admissions.nic.in"
            }
        )

    def get(self, url: str) -> httpx.Response:
        return self.client.get(url)

    def post(self, url: str, data: Dict[str, str]) -> httpx.Response:
        headers = self.client.headers.copy()
        headers["Referer"] = url
        return self.client.post(url, data=data, headers=headers)

    def stream_post(self, url: str, data: Dict[str, str]):
        headers = self.client.headers.copy()
        headers["Referer"] = url
        return self.client.stream("POST", url, data=data, headers=headers)

    def close(self):
        self.client.close()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()