import os
import tempfile
import hashlib
import logging
import socket
import ipaddress
from urllib.parse import urlparse, urljoin
import requests
import magic
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# --- Strict DTOs & Exceptions ---
class DownloadError(Exception): pass
class FileTooLargeError(DownloadError): pass
class InvalidMimeTypeError(DownloadError): pass
class MalformedHeaderError(DownloadError): pass
class SecurityViolationError(DownloadError): pass

@dataclass
class DownloadedMedia:
    temp_file_path: str
    mime_type: str
    extension: str
    content_hash: str
    byte_size: int

class SecureMediaDownloader:
    """
    Enterprise-grade streaming downloader. 
    Enforces memory safety, cryptographic hashing, and SSRF network containment.
    """
    CHUNK_SIZE = 8192
    TIMEOUT_TUPLE = (5, 15)
    MAX_REDIRECTS = 3
    
    ALLOWED_MIMES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp"
    }

    # Standard User-Agent to prevent basic 403 blocks from Cloudflare/AWS WAF
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/png,image/jpeg,*/*;q=0.8"
    }

    def _verify_ip_safety(self, url: str) -> None:
        """SSRF Firewall: Resolves all IPs unanimously, blocking private/internal routing."""
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            raise SecurityViolationError(f"Invalid URL structure: {url}")
            
        if parsed.scheme != "https":
            raise SecurityViolationError(f"Protocol '{parsed.scheme}' explicitly blocked. HTTPS required.")
        
        # Explicit IP Literal Check (Blocks URLs like https://127.0.0.1/image.png)
        try:
            parsed_literal = ipaddress.ip_address(hostname)
            if not parsed_literal.is_global:
                 raise SecurityViolationError(f"SSRF Blocked: Raw IP literal '{hostname}' is not a global public IP.")
        except ValueError:
            pass # Valid hostname string, proceed to DNS resolution
            
        try:
            # Unanimous DNS validation: Fetch all IPv4/IPv6 records
            addr_info = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
            for _, _, _, _, sockaddr in addr_info:
                ip = sockaddr[0]
                parsed_ip = ipaddress.ip_address(ip)
                if not parsed_ip.is_global:
                    raise SecurityViolationError(f"SSRF Blocked: Target '{hostname}' resolves to internal/private IP {ip}")
        except socket.gaierror:
            raise SecurityViolationError(f"DNS resolution failed for hostname {hostname}")

    def _get_safe_stream(self, url: str) -> requests.Response:
        """Executes HTTP GET while manually traversing redirects to enforce SSRF checks."""
        current_url = url
        
        for hop in range(self.MAX_REDIRECTS):
            self._verify_ip_safety(current_url)
            
            # Explicit security: verify=True, allow_redirects=False
            response = requests.get(
                current_url, 
                headers=self.DEFAULT_HEADERS,
                stream=True, 
                timeout=self.TIMEOUT_TUPLE, 
                allow_redirects=False,
                verify=True 
            )
            
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise DownloadError("Redirect missing Location header.")
                
                # Normalize relative paths to absolute URLs
                current_url = urljoin(current_url, location)
                response.close() # Free socket before following redirect
                continue
                
            response.raise_for_status()
            return response
            
        raise DownloadError(f"Exceeded maximum of {self.MAX_REDIRECTS} redirects.")

    def download_and_validate(self, url: str, max_bytes: int) -> DownloadedMedia:
        safe_hostname = urlparse(url).hostname or "unknown_host"
        temp_fd, temp_path = tempfile.mkstemp(prefix="derived_media_")
        os.close(temp_fd) 
        
        try:
            # Context manager guarantees socket closure on all exit paths
            with self._get_safe_stream(url) as response:
                
                # Strict Pre-Flight Content-Type Verification (Advisory Fail-Fast)
                declared_type = response.headers.get("Content-Type", "").lower()
                base_type = declared_type.split(";")[0].strip()
                
                if base_type and base_type not in self.ALLOWED_MIMES:
                     raise MalformedHeaderError(f"Rejected: Declared Content-Type '{declared_type}' is not an authorized image format.")

                # Pre-Flight Content-Length (Strict Fail-Closed)
                declared_length = response.headers.get("Content-Length")
                if declared_length:
                    try:
                        if int(declared_length) > max_bytes:
                            raise FileTooLargeError(f"Rejected: Declared size {declared_length} exceeds limit.")
                    except ValueError:
                        raise MalformedHeaderError("Rejected: Content-Length header is not a valid integer.")

                # The Air-Lock Stream & Incremental Hash
                bytes_received = 0
                hasher = hashlib.sha256()
                
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                        if chunk:
                            bytes_received += len(chunk)
                            
                            # Mathematical early-abort check with explicit TCP severing
                            if bytes_received > max_bytes:
                                response.close() 
                                raise FileTooLargeError(f"Rejected: Stream exceeded {max_bytes} byte limit.")
                                
                            f.write(chunk)
                            hasher.update(chunk)
                            
            if bytes_received == 0:
                raise DownloadError("Rejected: Zero bytes downloaded.")

            # C-Level Magic Byte Inspection (The Ultimate Source of Truth)
            actual_mime = magic.from_file(temp_path, mime=True)
            if actual_mime not in self.ALLOWED_MIMES:
                raise InvalidMimeTypeError(f"Rejected: Magic byte detected invalid MIME '{actual_mime}'.")

            if base_type and actual_mime not in base_type:
                logger.warning(f"[Downloader] Spoof Detected on {safe_hostname}: Header claimed {base_type}, Magic proved {actual_mime}")

            return DownloadedMedia(
                temp_file_path=temp_path,
                mime_type=actual_mime,
                extension=self.ALLOWED_MIMES[actual_mime],
                content_hash=hasher.hexdigest(),
                byte_size=bytes_received
            )

        except Exception as e:
            # Downloader cleans up after itself on failure. Caller cleans up on success.
            if os.path.exists(temp_path):
                os.remove(temp_path)
            # Prevent logging the raw URL to avoid leaking query parameters
            logger.warning(f"[Downloader] Failed to acquire from {safe_hostname} - {type(e).__name__}: {str(e)}")
            raise