import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import hashlib
import json

try:
    from bs4 import BeautifulSoup
    import html2text
    from readability import Document
    import lxml
except ImportError as e:
    print(f"Warning: Web scraping libraries not available: {e}")
    print("Install with: pip install beautifulsoup4 html2text readability-lxml lxml")

@dataclass
class WebContent:
    url: str
    title: str
    content: str
    summary: str
    metadata: Dict[str, Any]
    scraped_at: datetime
    content_type: str
    word_count: int
    links: List[str] = None
    images: List[str] = None

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    relevance_score: float = 0.0

class WebScraper:
    """Web scraping and content extraction system"""
    
    def __init__(self, cache_dir: str = ".mcp_web_cache"):
        self.cache_dir = cache_dir
        self.cache: Dict[str, WebContent] = {}
        self.cache_duration = timedelta(hours=24)  # Cache for 24 hours
        
        # User agent for requests
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        # HTML to text converter
        try:
            self.html_converter = html2text.HTML2Text()
            self.html_converter.ignore_links = False
            self.html_converter.ignore_images = False
            self.html_converter.body_width = 0
        except:
            self.html_converter = None
    
    async def scrape_url(self, url: str, use_cache: bool = True) -> Optional[WebContent]:
        """Scrape content from a URL"""
        
        # Check cache first
        if use_cache:
            cached_content = self._get_cached_content(url)
            if cached_content:
                return cached_content
        
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'text/html' in content_type:
                            html_content = await response.text()
                            web_content = await self._parse_html_content(url, html_content)
                            
                            # Cache the content
                            if use_cache:
                                self._cache_content(url, web_content)
                            
                            return web_content
                        else:
                            # Handle non-HTML content
                            text_content = await response.text()
                            return WebContent(
                                url=url,
                                title=self._extract_title_from_url(url),
                                content=text_content,
                                summary=text_content[:500] + "..." if len(text_content) > 500 else text_content,
                                metadata={'content_type': content_type},
                                scraped_at=datetime.now(),
                                content_type=content_type,
                                word_count=len(text_content.split())
                            )
                    else:
                        print(f"Failed to fetch {url}: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    async def _parse_html_content(self, url: str, html_content: str) -> WebContent:
        """Parse HTML content and extract meaningful information"""
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Extract title
            title = self._extract_title(soup, url)
            
            # Use readability to extract main content
            try:
                doc = Document(html_content)
                main_content = doc.summary()
                main_soup = BeautifulSoup(main_content, 'lxml')
            except:
                # Fallback to manual content extraction
                main_soup = self._extract_main_content(soup)
            
            # Convert to text
            if self.html_converter:
                text_content = self.html_converter.handle(str(main_soup))
            else:
                text_content = main_soup.get_text(separator='\n', strip=True)
            
            # Clean up text
            text_content = self._clean_text(text_content)
            
            # Extract metadata
            metadata = self._extract_metadata(soup)
            
            # Extract links and images
            links = self._extract_links(soup, url)
            images = self._extract_images(soup, url)
            
            # Create summary
            summary = self._create_summary(text_content)
            
            return WebContent(
                url=url,
                title=title,
                content=text_content,
                summary=summary,
                metadata=metadata,
                scraped_at=datetime.now(),
                content_type='text/html',
                word_count=len(text_content.split()),
                links=links[:10],  # Limit to 10 links
                images=images[:5]  # Limit to 5 images
            )
            
        except Exception as e:
            print(f"Error parsing HTML content: {e}")
            return WebContent(
                url=url,
                title=self._extract_title_from_url(url),
                content=html_content[:1000],
                summary="Failed to parse content",
                metadata={},
                scraped_at=datetime.now(),
                content_type='text/html',
                word_count=0
            )
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract page title"""
        # Try different title sources
        title_sources = [
            soup.find('title'),
            soup.find('h1'),
            soup.find('meta', property='og:title'),
            soup.find('meta', name='twitter:title')
        ]
        
        for source in title_sources:
            if source:
                if source.name == 'meta':
                    title = source.get('content', '').strip()
                else:
                    title = source.get_text().strip()
                
                if title:
                    return title[:200]  # Limit title length
        
        return self._extract_title_from_url(url)
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract title from URL as fallback"""
        parsed = urlparse(url)
        return parsed.netloc + parsed.path
    
    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract main content from HTML (fallback method)"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            element.decompose()
        
        # Try to find main content areas
        main_selectors = [
            'main',
            'article',
            '.content',
            '.main-content',
            '#content',
            '#main',
            '.post-content',
            '.entry-content'
        ]
        
        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                return main_content
        
        # Fallback to body
        body = soup.find('body')
        return body if body else soup
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from HTML"""
        metadata = {}
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content')
            if name and content:
                metadata[name] = content
        
        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag.get('lang')
        
        return metadata
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links from HTML"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            if full_url.startswith(('http://', 'https://')):
                links.append(full_url)
        return list(set(links))  # Remove duplicates
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs from HTML"""
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            full_url = urljoin(base_url, src)
            if full_url.startswith(('http://', 'https://')):
                images.append(full_url)
        return list(set(images))  # Remove duplicates
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove very short lines (likely navigation/UI elements)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 10 or not line:  # Keep empty lines for formatting
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _create_summary(self, text: str, max_length: int = 500) -> str:
        """Create a summary of the text content"""
        if len(text) <= max_length:
            return text
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        summary = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if len(summary) + len(sentence) + 1 <= max_length:
                summary += sentence + ". "
            else:
                break
        
        return summary.strip()
    
    def _get_cached_content(self, url: str) -> Optional[WebContent]:
        """Get cached content if available and not expired"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        if url_hash in self.cache:
            content = self.cache[url_hash]
            if datetime.now() - content.scraped_at < self.cache_duration:
                return content
            else:
                # Remove expired content
                del self.cache[url_hash]
        
        return None
    
    def _cache_content(self, url: str, content: WebContent):
        """Cache web content"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        self.cache[url_hash] = content
        
        # Simple cache size management
        if len(self.cache) > 100:  # Keep only 100 most recent items
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].scraped_at)
            del self.cache[oldest_key]
    
    async def scrape_multiple_urls(self, urls: List[str], max_concurrent: int = 5) -> List[WebContent]:
        """Scrape multiple URLs concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        valid_results = []
        for result in results:
            if isinstance(result, WebContent):
                valid_results.append(result)
            elif isinstance(result, Exception):
                print(f"Scraping error: {result}")
        
        return valid_results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_items': len(self.cache),
            'cache_duration_hours': self.cache_duration.total_seconds() / 3600,
            'oldest_item': min(self.cache.values(), key=lambda x: x.scraped_at).scraped_at.isoformat() if self.cache else None,
            'newest_item': max(self.cache.values(), key=lambda x: x.scraped_at).scraped_at.isoformat() if self.cache else None
        }
