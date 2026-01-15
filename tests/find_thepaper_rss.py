"""
Try different The Paper RSS URLs
"""
import requests
import xml.etree.ElementTree as ET

# 尝试不同的澎湃新闻RSS地址
urls = [
    "https://www.thepaper.cn/rss_news.jsp",
    "https://www.thepaper.cn/rss.jsp",
    "https://m.thepaper.cn/rss.jsp",
    "https://www.thepaper.cn/channel_rss/25950",  # 时事
    "https://www.thepaper.cn/feed",
]

for url in urls:
    print(f"\n{'='*80}")
    print(f"Trying: {url}")
    print('='*80)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        content_type = response.headers.get('Content-Type', '')
        print(f"Content-Type: {content_type}")
        
        # Check if it's XML
        if 'xml' in content_type or response.text.strip().startswith('<?xml'):
            print("✅ Looks like XML!")
            try:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                print(f"✅ Found {len(items)} items")
                
                if items:
                    print("\nFirst item:")
                    item = items[0]
                    print(f"  Title: {item.findtext('title')}")
                    print(f"  Link: {item.findtext('link')}")
                    
            except Exception as e:
                print(f"❌ XML parsing failed: {e}")
        else:
            print("❌ Not XML content")
            print(f"First 200 chars: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

print("\n" + "="*80)
print("Testing complete!")
