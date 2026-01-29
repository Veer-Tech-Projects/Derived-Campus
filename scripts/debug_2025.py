import requests
from bs4 import BeautifulSoup
import re
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://cetonline.karnataka.gov.in/kea/ugcet2025"

# Use a strong User-Agent to look like Chrome
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
}

def probe():
    print(f"🕵️  Probing {URL}...")
    
    try:
        response = requests.get(URL, headers=HEADERS, verify=False, timeout=20)
        print(f"✅ Connection Success! Status: {response.status_code}")
        print(f"📄 Page Size: {len(response.text)} bytes")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("\n" + "="*50)
    print("🔍 DIAGNOSTIC 1: SEARCHING FOR 'CUTOFF' TEXT")
    print("="*50)
    
    # Find any text node containing "CUT" (case insensitive)
    text_matches = soup.find_all(string=re.compile(r"CUT", re.IGNORECASE))
    
    if not text_matches:
        print("❌ CRITICAL FAILURE: No text containing 'CUT' was found in the HTML.")
        print("   This means the server is sending a blank/different page to Python.")
        print("   Dumping first 500 chars of body to check for Captcha/Error:")
        print(soup.body.get_text()[:500] if soup.body else "No Body Tag")
    else:
        for i, text in enumerate(text_matches):
            print(f"\n[Match {i+1}] Text: '{text.strip()}'")
            parent = text.parent
            print(f"   Parent Tag: <{parent.name}>")
            print(f"   Attributes: {parent.attrs}")
            
            # Check for Bootstrap attributes
            if 'data-target' in parent.attrs:
                print(f"   🎯 FOUND DATA-TARGET: {parent['data-target']}")
            elif parent.parent and 'data-target' in parent.parent.attrs:
                print(f"   🎯 FOUND PARENT DATA-TARGET: {parent.parent['data-target']}")
            else:
                print("   ⚠️  NO BOOTSTRAP TOGGLE FOUND HERE")

    print("\n" + "="*50)
    print("🔍 DIAGNOSTIC 2: SEARCHING FOR BOOTSTRAP TOGGLES")
    print("="*50)
    
    toggles = soup.find_all(attrs={"data-toggle": "collapse"})
    toggles += soup.find_all(attrs={"data-target": True})
    
    unique_toggles = list(set(toggles))
    print(f"Found {len(unique_toggles)} interactive elements.")
    
    for t in unique_toggles[:5]: # Print first 5
        print(f" - <{t.name}> Text: '{t.get_text(strip=True)[:30]}...' | Target: {t.get('data-target')}")

if __name__ == "__main__":
    probe()