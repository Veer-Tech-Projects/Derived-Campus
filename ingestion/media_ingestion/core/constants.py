from typing import Final, Tuple

# --- Domain Governance ---
# Hard blacklist: permanently excluded domains
NOISE_DOMAINS: Final[Tuple[str, ...]] = (
    "pinterest.com",
    "shiksha.com",
    "collegedunia.com",
    "collegedekho.com",
    "justdial.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "getmyuni.com"
)

# Authority preference (ranking boost)
AUTHORITY_TLDS: Final[Tuple[str, ...]] = (
    ".ac.in",
    ".edu.in",
    ".gov.in",
)

# --- Query Templates ---
LOGO_QUERY_TEMPLATE: Final[str] = "{canonical_name} {city} logo high resolution png"
CAMPUS_HERO_QUERY_TEMPLATE: Final[str] = "{canonical_name} {city} campus building main entrance high resolution"

# --- Dimensional Guardrails (Enterprise Defense) ---
# Logos
LOGO_MIN_WIDTH: Final[int] = 150
LOGO_MIN_HEIGHT: Final[int] = 150
LOGO_MAX_ASPECT_RATIO: Final[float] = 3.0 
LOGO_MAX_BYTES: Final[int] = 1 * 1024 * 1024     # 1 MB

# Campus Hero
CAMPUS_MIN_WIDTH: Final[int] = 800
CAMPUS_MIN_HEIGHT: Final[int] = 500
CAMPUS_MAX_BYTES: Final[int] = 5 * 1024 * 1024   # 5 MB

# --- Rate Limiting Defaults ---
DEFAULT_REQUEST_TIMEOUT_SEC: Final[int] = 10
DEFAULT_RETRY_ATTEMPTS: Final[int] = 3