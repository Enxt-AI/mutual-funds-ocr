"""Try different AES key interpretations for JM Financial."""
import requests
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding

KEY_STR = "6fa979f20126cb08aa645a8f495f6d85"
IV_STR = "I8zyA4lVhMCaJ5Kg"

# Get encrypted data
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.jmfinancialmf.com",
    "Referer": "https://www.jmfinancialmf.com/",
}
r = requests.post("https://jmmfapi.jmfinancialmf.com/api/GetFactsheet", json={}, headers=headers, timeout=15)
encrypted = r.json()["data"]
print(f"Encrypted: {encrypted[:80]}...")

# Try different key/IV combos
key_options = [
    ("key as UTF-8 (32 bytes, AES-256)", KEY_STR.encode('utf-8'), IV_STR.encode('utf-8')),
    ("key as hex (16 bytes, AES-128)", bytes.fromhex(KEY_STR), IV_STR.encode('utf-8')),
    ("key as UTF-8, IV as UTF-8 (16 bytes each, trim key)", KEY_STR[:16].encode('utf-8'), IV_STR.encode('utf-8')),
]

for label, key, iv in key_options:
    print(f"\n=== {label} ===")
    print(f"  Key: {key.hex()} ({len(key)} bytes)")
    print(f"  IV:  {iv.hex()} ({len(iv)} bytes)")
    try:
        ct = base64.b64decode(encrypted)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        dec = cipher.decryptor()
        padded = dec.update(ct) + dec.finalize()
        
        # Try PKCS7 unpadding
        try:
            unpadder = sym_padding.PKCS7(128).unpadder()
            pt = unpadder.update(padded) + unpadder.finalize()
            result = pt.decode('utf-8')
            print(f"  SUCCESS (PKCS7)! Length: {len(result)}")
            print(f"  Data: {result[:1000]}")
        except ValueError:
            # Try without padding (maybe zero-padded)
            result = padded.rstrip(b'\x00').decode('utf-8', errors='replace')
            if result and result[0] in '[{':
                print(f"  SUCCESS (zero-pad)! Length: {len(result)}")
                print(f"  Data: {result[:1000]}")
            else:
                print(f"  Padding failed. Raw last 16 bytes: {padded[-16:].hex()}")
                print(f"  Raw first 50 bytes (as text): {padded[:50]}")
    except Exception as e:
        print(f"  ERROR: {e}")
