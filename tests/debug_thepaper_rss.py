"""
Debug The Paper RSS response
"""
import requests
import xml.etree.ElementTree as ET

RSS_URL = "https://www.thepaper.cn/rss_news.jsp"

print(f"Fetching RSS from: {RSS_URL}")

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(RSS_URL, headers=headers, timeout=10)
    response.encoding = 'utf-8'
    
    print(f"Status Code: {response.status_code}")
    print(f"Content Type: {response.headers.get('Content-Type')}")
    print(f"Content Length: {len(response.content)} bytes")
    print("\n" + "="*80)
    print("First 2000 characters of response:")
    print("="*80)
    print(response.text[:2000])
    print("\n" + "="*80)
    
    # Try to parse XML
    try:
        root = ET.fromstring(response.content)
        print("\n✅ XML parsed successfully!")
        print(f"Root tag: {root.tag}")
        
        # Find channel
        channel = root.find('.//channel')
        if channel:
            print(f"Channel found: {channel.tag}")
            title = channel.findtext('title')
            print(f"Channel title: {title}")
        
        # Find all items
        items = root.findall('.//item')
        print(f"\nTotal items found: {len(items)}")
        
        if items:
            print("\n" + "="*80)
            print("First 3 items:")
            print("="*80)
            for idx, item in enumerate(items[:3], 1):
                print(f"\nItem {idx}:")
                print(f"  Title: {item.findtext('title')}")
                print(f"  Link: {item.findtext('link')}")
                print(f"  PubDate: {item.findtext('pubDate')}")
                desc = item.findtext('description')
                if desc:
                    print(f"  Description: {desc[:200]}...")
                
                # Check all child elements
                print(f"  All elements: {[child.tag for child in item]}")
        
    except ET.ParseError as e:
        print(f"\n❌ XML parsing failed: {e}")
        
except Exception as e:
    print(f"\n❌ Request failed: {e}")
    import traceback
    traceback.print_exc()
