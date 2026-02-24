"""Test ITI AMC API with AES encryption using cryptography lib."""
import requests
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding

# Encryption params from JS bundle
KEY = b"aar6tzij8o1snaar"  # 16 bytes
IV  = b"0123456789ABCDEF"  # 16 bytes

def encrypt_data(plaintext: str) -> str:
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
    enc = cipher.encryptor()
    ct = enc.update(padded) + enc.finalize()
    return base64.b64encode(ct).decode('utf-8')

def decrypt_data(ciphertext: str) -> str:
    ct = base64.b64decode(ciphertext)
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
    dec = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()
    return plaintext.decode('utf-8')

# Encrypt the payload
payload = json.dumps({"type": "downloads"})
encrypted = encrypt_data(payload)
print(f"Payload: {payload}")
print(f"Encrypted: {encrypted}")

# Send the request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.itiamc.com",
    "Referer": "https://www.itiamc.com/",
}

url = "https://itiamc.com/jeeth/api/v1/catalog/getDocumentsByType"
body = {"eData": encrypted}
print(f"\nPOST {url}")

r = requests.post(url, json=body, headers=headers, timeout=15)
print(f"Status: {r.status_code}, {len(r.text)} chars")

if r.status_code == 200:
    resp = r.json()
    print(f"Response keys: {list(resp.keys())}")

    # Check if response is encrypted
    if 'eData' in resp:
        decrypted = decrypt_data(resp['eData'])
        data = json.loads(decrypted)
    elif 'data' in resp:
        data = resp
    else:
        data = resp

    # Navigate to documentList
    inner = data.get('data', data) if isinstance(data, dict) else data
    doc_list = inner.get('documentList', []) if isinstance(inner, dict) else []
    print(f"\ndocumentList: {len(doc_list)} topics")
    for i, topic in enumerate(doc_list):
        name = topic.get('topic', '')
        items = topic.get('returnList', [])
        print(f"  [{i}] {name}: {len(items)} items")
        if 'factsheet' in name.lower():
            for j, item in enumerate(items[:5]):
                print(f"    [{j}] {json.dumps(item)[:400]}")
else:
    print(f"Response: {r.text[:500]}")
