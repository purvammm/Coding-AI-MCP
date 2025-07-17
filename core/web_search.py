import asyncio
import aiohttp
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin

try:
    from duckduckgo_search import DDGS
    from googlesearch import search as google_search
except ImportError as e:
    print(f"Warning: Search libraries not available: {e}")
    print("Install with: pip install duckduckgo-search googlesearch-python")

from .web_scraper import WebScraper, SearchResult, WebContent

@dataclass
class SearchQuery:
    query: str
    num_results: int = 10
    search_type: str = "web"  # web, images, news, videos
    language: str = "en"
    region: str = "us"
    safe_search: bool = True

class WebSearchEngine:
    """Comprehensive web search engine with multiple providers"""
    
    def __init__(self, web_scraper: WebScraper):
        self.web_scraper = web_scraper
        self.search_providers = {
            'duckduckgo': self._search_duckduckgo,
            'bing': self._search_bing,
            'serper': self._search_serper,
            'google_custom': self._search_google_custom
        }
        
        # API keys for various search services
        self.bing_api_key = None
        self.serper_api_key = None
        self.google_cse_id = None
        self.google_api_key = None
    
    def configure_apis(self, **api_keys):
        """Configure API keys for search services"""
        self.bing_api_key = api_keys.get('bing_api_key')
        self.serper_api_key = api_keys.get('serper_api_key')
        self.google_cse_id = api_keys.get('google_cse_id')
        self.google_api_key = api_keys.get('google_api_key')
    
    async def search(
        self, 
        query: str, 
        num_results: int = 10,
        provider: str = "duckduckgo",
        include_content: bool = False
    ) -> List[SearchResult]:
        """Perform web search using specified provider"""
        
        search_query = SearchQuery(
            query=query,
            num_results=num_results
        )
        
        if provider in self.search_providers:
            try:
                results = await self.search_providers[provider](search_query)
                
                # Optionally fetch full content for each result
                if include_content and results:
                    results = await self._enrich_results_with_content(results)
                
                return results
            except Exception as e:
                print(f"Search error with {provider}: {e}")
                return []
        else:
            raise ValueError(f"Unknown search provider: {provider}")
    
    async def multi_provider_search(
        self, 
        query: str, 
        num_results: int = 10,
        providers: List[str] = None
    ) -> Dict[str, List[SearchResult]]:
        """Search using multiple providers and combine results"""
        
        if providers is None:
            providers = ['duckduckgo', 'bing']
        
        results = {}
        tasks = []
        
        for provider in providers:
            if provider in self.search_providers:
                task = self.search(query, num_results, provider)
                tasks.append((provider, task))
        
        # Execute searches concurrently
        for provider, task in tasks:
            try:
                provider_results = await task
                results[provider] = provider_results
            except Exception as e:
                print(f"Error with {provider}: {e}")
                results[provider] = []
        
        return results
    
    async def _search_duckduckgo(self, query: SearchQuery) -> List[SearchResult]:
        """Search using DuckDuckGo"""
        try:
            ddgs = DDGS()
            results = []
            
            # Perform search
            search_results = ddgs.text(
                query.query,
                max_results=query.num_results,
                region=query.region,
                safesearch='moderate' if query.safe_search else 'off'
            )
            
            for i, result in enumerate(search_results):
                search_result = SearchResult(
                    title=result.get('title', ''),
                    url=result.get('href', ''),
                    snippet=result.get('body', ''),
                    source='duckduckgo',
                    relevance_score=1.0 - (i * 0.1)  # Decreasing relevance
                )
                results.append(search_result)
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return []
    
    async def _search_bing(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Bing Search API"""
        if not self.bing_api_key:
            print("Bing API key not configured")
            return []
        
        try:
            headers = {
                'Ocp-Apim-Subscription-Key': self.bing_api_key,
                'User-Agent': 'Mozilla/5.0 (compatible; MSIE 10.0; Windows Phone 8.0; Trident/6.0; IEMobile/10.0; ARM; Touch; NOKIA; Lumia 822)'
            }
            
            params = {
                'q': query.query,
                'count': query.num_results,
                'mkt': f"{query.language}-{query.region}",
                'safeSearch': 'Moderate' if query.safe_search else 'Off'
            }
            
            url = "https://api.bing.microsoft.com/v7.0/search"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        web_pages = data.get('webPages', {}).get('value', [])
                        for i, page in enumerate(web_pages):
                            search_result = SearchResult(
                                title=page.get('name', ''),
                                url=page.get('url', ''),
                                snippet=page.get('snippet', ''),
                                source='bing',
                                relevance_score=1.0 - (i * 0.1)
                            )
                            results.append(search_result)
                        
                        return results
                    else:
                        print(f"Bing API error: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"Bing search error: {e}")
            return []
    
    async def _search_serper(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Serper API"""
        if not self.serper_api_key:
            print("Serper API key not configured")
            return []
        
        try:
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query.query,
                'num': query.num_results,
                'gl': query.region,
                'hl': query.language
            }
            
            url = "https://google.serper.dev/search"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        organic_results = data.get('organic', [])
                        for i, result in enumerate(organic_results):
                            search_result = SearchResult(
                                title=result.get('title', ''),
                                url=result.get('link', ''),
                                snippet=result.get('snippet', ''),
                                source='serper',
                                relevance_score=1.0 - (i * 0.1)
                            )
                            results.append(search_result)
                        
                        return results
                    else:
                        print(f"Serper API error: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"Serper search error: {e}")
            return []
    
    async def _search_google_custom(self, query: SearchQuery) -> List[SearchResult]:
        """Search using Google Custom Search API"""
        if not self.google_api_key or not self.google_cse_id:
            print("Google Custom Search API credentials not configured")
            return []
        
        try:
            params = {
                'key': self.google_api_key,
                'cx': self.google_cse_id,
                'q': query.query,
                'num': min(query.num_results, 10),  # Google CSE max is 10
                'gl': query.region,
                'hl': query.language,
                'safe': 'active' if query.safe_search else 'off'
            }
            
            url = "https://www.googleapis.com/customsearch/v1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        items = data.get('items', [])
                        for i, item in enumerate(items):
                            search_result = SearchResult(
                                title=item.get('title', ''),
                                url=item.get('link', ''),
                                snippet=item.get('snippet', ''),
                                source='google_custom',
                                relevance_score=1.0 - (i * 0.1)
                            )
                            results.append(search_result)
                        
                        return results
                    else:
                        print(f"Google Custom Search API error: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"Google Custom Search error: {e}")
            return []
    
    async def _enrich_results_with_content(self, results: List[SearchResult]) -> List[SearchResult]:
        """Fetch full content for search results"""
        enriched_results = []
        
        # Limit concurrent requests
        semaphore = asyncio.Semaphore(3)
        
        async def fetch_content(result: SearchResult):
            async with semaphore:
                try:
                    web_content = await self.web_scraper.scrape_url(result.url)
                    if web_content:
                        # Add content to the search result
                        result.snippet = web_content.summary
                        # Store full content in a custom attribute
                        result.full_content = web_content.content
                        result.word_count = web_content.word_count
                    return result
                except Exception as e:
                    print(f"Error fetching content for {result.url}: {e}")
                    return result
        
        tasks = [fetch_content(result) for result in results]
        enriched_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in enriched_results:
            if isinstance(result, SearchResult):
                valid_results.append(result)
        
        return valid_results
    
    async def search_and_summarize(
        self, 
        query: str, 
        num_results: int = 5,
        provider: str = "duckduckgo"
    ) -> Dict[str, Any]:
        """Search and provide a comprehensive summary"""
        
        # Perform search
        results = await self.search(query, num_results, provider, include_content=True)
        
        if not results:
            return {
                "query": query,
                "results_count": 0,
                "summary": "No results found",
                "sources": []
            }
        
        # Create summary
        summary_parts = [f"Search results for: {query}\n"]
        sources = []
        
        for i, result in enumerate(results, 1):
            summary_parts.append(f"{i}. **{result.title}**")
            summary_parts.append(f"   Source: {result.url}")
            summary_parts.append(f"   {result.snippet}")
            summary_parts.append("")
            
            sources.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "relevance_score": result.relevance_score
            })
        
        return {
            "query": query,
            "results_count": len(results),
            "summary": "\n".join(summary_parts),
            "sources": sources,
            "search_provider": provider,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_available_providers(self) -> List[str]:
        """Get list of available search providers"""
        available = ['duckduckgo']  # Always available
        
        if self.bing_api_key:
            available.append('bing')
        if self.serper_api_key:
            available.append('serper')
        if self.google_api_key and self.google_cse_id:
            available.append('google_custom')
        
        return available
