import requests
import json
import time

BASE_URL = "http://127.0.0.1:3000/api"

print("--- 1. Testing /config ---")
res = requests.get(f"{BASE_URL}/config")
print(json.dumps(res.json(), indent=2))
print()

print("--- 2. Testing /scan (Source: RBI) ---")
start = time.time()
res = requests.post(f"{BASE_URL}/scan", json={"source": "RBI"})
scan_data = res.json()
print(f"Scan completed in {time.time() - start:.2f}s")
print(f"Success: {scan_data.get('success')}")
print(f"Count: {scan_data.get('count', 0)}")
if scan_data.get("regulations") and len(scan_data["regulations"]) > 0:
    reg = scan_data["regulations"][0]
    print("\nFirst Regulation:")
    print(f"Title: {reg.get('title')}")
    print(f"Date: {reg.get('date')}")
    
    print("\n--- 3. Testing /analyze on First Regulation ---")
    start = time.time()
    res = requests.post(f"{BASE_URL}/analyze", json={"regulation": reg})
    analyze_data = res.json()
    print(f"Analysis completed in {time.time() - start:.2f}s")
    print(f"Success: {analyze_data.get('success')}")
    print("\nAnalysis Snippet:")
    print(analyze_data.get("analysis", "")[:500] + "...")
else:
    print("No regulations returned.")
