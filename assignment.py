import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional

class BulletproofScraper:
    def __init__(self, team_id: str = "aline123"):
        self.team_id = team_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def find_content_links(self, base_url: str) -> List[str]:
        """Find content links without any Tag operations that could cause errors"""
        try:
            print(f"🔍 Finding content links from: {base_url}")
            
            response = self.session.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            links = set()
            
            # Simple approach: find all links and filter them
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href')
                if not href:
                    continue
                
                # Convert to absolute URL
                full_url = urljoin(base_url, href)
                
                # Check if it's a valid content link
                if self._is_content_link(full_url, base_url):
                    links.add(full_url)
            
            links_list = list(links)[:20]  # Limit for demo
            print(f"✅ Found {len(links_list)} content links")
            
            # Show first few
            for i, link in enumerate(links_list[:3]):
                print(f"  {i+1}. {link}")
            
            return links_list
            
        except Exception as e:
            print(f"❌ Error finding links: {e}")
            return []
    
    def _is_content_link(self, url: str, base_url: str) -> bool:
        """Check if URL is a content link"""
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(base_url)
            
            # Must be same domain
            if parsed_url.netloc != parsed_base.netloc:
                return False
                
            path = parsed_url.path.lower()
            
            # Skip obvious non-content
            skip_patterns = [
                '#', '.pdf', '.jpg', '.png', '.css', '.js',
                '/search', '/tag/', '/category/', '/author/',
                '/page/', '/feed', '/rss'
            ]
            
            if any(pattern in url.lower() for pattern in skip_patterns):
                return False
            
            # Look for content patterns
            content_patterns = [
                '/blog/', '/post/', '/article/', '/guide/', '/learn/'
            ]
            
            if any(pattern in path for pattern in content_patterns):
                # Must not be the base path itself
                if url != base_url and len(path.split('/')) > 2:
                    return True
            
            return False
            
        except:
            return False
    
    def scrape_content(self, url: str) -> Optional[Dict]:
        """Scrape content with bulletproof approach"""
        try:
            print(f"📄 Scraping: {url}")
            
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            unwanted_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside']
            for tag_name in unwanted_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            
            # Extract title - simple approach
            title = self._extract_title_simple(soup)
            
            # Extract content - very simple approach
            content = self._extract_content_simple(soup)
            
            if not title or len(content) < 100:
                print(f"  ⚠️ Skipping - insufficient content")
                return None
            
            # Determine content type
            content_type = "guide" if "/guide" in url.lower() else "blog"
            
            print(f"  ✅ Success! Title: {title[:50]}...")
            
            return {
                "title": title,
                "content": content,
                "content_type": content_type,
                "source_url": url,
                "author": "",
                "user_id": ""
            }
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None
    
    def _extract_title_simple(self, soup: BeautifulSoup) -> str:
        """Extract title with simple, safe approach"""
        try:
            # Try h1 first
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
                if len(title) > 5:
                    return title
            
            # Try title tag
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                if len(title) > 5:
                    return title
            
            return "Untitled Article"
            
        except:
            return "Untitled Article"
    
    def _extract_content_simple(self, soup: BeautifulSoup) -> str:
        """Extract content with bulletproof approach - no Tag comparisons"""
        try:
            # Strategy 1: Find article or main tag
            content_container = soup.find('article')
            if not content_container:
                content_container = soup.find('main')
            
            # Strategy 2: Find by common content classes
            if not content_container:
                for class_name in ['content', 'post-content', 'entry-content', 'article-content']:
                    content_container = soup.find(class_=class_name)
                    if content_container:
                        break
            
            # Strategy 3: Use the whole body if nothing else works
            if not content_container:
                content_container = soup.find('body')
                if not content_container:
                    content_container = soup
            
            # Now extract text in a safe way
            return self._convert_to_markdown_safe(content_container)
            
        except Exception as e:
            print(f"  ⚠️ Content extraction error: {e}")
            try:
                return soup.get_text(separator='\n', strip=True)[:2000]
            except:
                return "Error extracting content"
    
    def _convert_to_markdown_safe(self, element) -> str:
        """Convert to markdown without any operations that could cause Tag comparisons"""
        try:
            text_parts = []
            
            # Get all text, but try to preserve some structure
            # Method 1: Process headers
            try:
                for i in range(1, 7):  # h1 to h6
                    headers = element.find_all(f'h{i}')
                    for header in headers:
                        header_text = header.get_text(strip=True)
                        if header_text:
                            text_parts.append(f"{'#' * i} {header_text}\n\n")
            except:
                pass
            
            # Method 2: Process paragraphs
            try:
                paragraphs = element.find_all('p')
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if p_text and len(p_text) > 20:
                        text_parts.append(f"{p_text}\n\n")
            except:
                pass
            
            # Method 3: Process code blocks
            try:
                code_blocks = element.find_all('pre')
                for code in code_blocks:
                    code_text = code.get_text()
                    if code_text.strip():
                        text_parts.append(f"```\n{code_text}\n```\n\n")
            except:
                pass
            
            # If we got structured content, use it
            if text_parts:
                content = ''.join(text_parts)
            else:
                # Fallback: just get all text
                content = element.get_text(separator='\n\n', strip=True)
            
            # Clean up
            content = re.sub(r'\n{3,}', '\n\n', content)
            return content.strip()
            
        except Exception as e:
            print(f"  ⚠️ Markdown conversion error: {e}")
            # Ultimate safe fallback
            try:
                return element.get_text(strip=True)
            except:
                return "Content extraction failed"
    
    def scrape_all_sources(self, sources: List[str]) -> List[Dict]:
        """Scrape all sources"""
        all_items = []
        
        for i, source in enumerate(sources):
            print(f"\n{'='*60}")
            print(f"🚀 Source {i+1}/{len(sources)}: {source}")
            print(f"{'='*60}")
            
            try:
                # Find links
                links = self.find_content_links(source)
                
                if not links:
                    print(f"No links found for {source}")
                    continue
                
                # Scrape each link
                source_items = []
                for j, link in enumerate(links):
                    print(f"\n--- Processing {j+1}/{len(links)} ---")
                    
                    item = self.scrape_content(link)
                    if item:
                        all_items.append(item)
                        source_items.append(item)
                    
                    time.sleep(1)  # Be respectful
                
                print(f"\n✅ Source completed: {len(source_items)} items from {source}")
                
            except Exception as e:
                print(f"❌ Source failed: {e}")
        
        return all_items
    
    def save_results(self, items: List[Dict], filename: str = "knowledge_base.json"):
        """Save results"""
        result = {
            "team_id": self.team_id,
            "items": items
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(items)} items to {filename}")
        return result

def main():
    """Main function"""
    print("🎯 Bulletproof Universal Knowledge Base Scraper")
    print("=" * 60)
    
    # Sources to scrape
    sources = [
        "https://interviewing.io/blog",
        "https://interviewing.io/topics#companies",
        "https://interviewing.io/learn#interview-guides",
        "https://nilmamano.com/blog/category/dsa",
        "https://quill.co/blog",
        "https://shreycation.substack.com"
    ]
    
    print(f"📋 Scraping {len(sources)} sources:")
    for i, source in enumerate(sources, 1):
        print(f"  {i}. {source}")
    
    # Initialize scraper
    scraper = BulletproofScraper(team_id="aline123")
    
    # Scrape all sources
    all_items = scraper.scrape_all_sources(sources)
    
    # Save results
    scraper.save_results(all_items, "aline_knowledge_base.json")
    
    # Print summary
    print(f"\n📊 FINAL RESULTS")
    print(f"=" * 60)
    print(f"Total items scraped: {len(all_items)}")
    
    # Count by type
    type_counts = {}
    for item in all_items:
        t = item['content_type']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    for content_type, count in type_counts.items():
        print(f"  {content_type}: {count} items")
    
    # Show sample
    if all_items:
        print(f"\n📄 Sample item:")
        sample = all_items[0]
        print(f"Title: {sample['title']}")
        print(f"Type: {sample['content_type']}")
        print(f"Content preview: {sample['content'][:200]}...")
    
    print(f"\n🎉 Complete! Check 'aline_knowledge_base.json'")

if __name__ == "__main__":
    main()