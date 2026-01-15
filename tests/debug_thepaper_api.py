"""
Debug The Paper API response
"""
import requests

API_URL = "https://www.thepaper.cn/api/search/web"

params = {
    'query': '科技',
    'page': 1,
    'pageSize': 10
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"Testing API: {API_URL}")
print(f"Params: {params}")
print("\n" + "="*80)

try:
    response = requests.get(API_URL, params=params, headers=headers, timeout=10)
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Content Length: {len(response.content)} bytes")
    print("\n" + "="*80)
    print("Response content (first 1000 chars):")
    print("="*80)
    print(response.text[:1000])
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
