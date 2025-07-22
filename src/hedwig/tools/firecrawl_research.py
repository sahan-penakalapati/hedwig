"""
Firecrawl Research Tool for web research and content extraction.

This tool handles web research tasks using the Firecrawl service for
intelligent web scraping, content extraction, and data gathering.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse

try:
    from firecrawl import FirecrawlApp
except ImportError:
    FirecrawlApp = None

import requests
from pydantic import BaseModel, Field, validator

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.core.logging_config import get_logger
from hedwig.tools.base import Tool


class FirecrawlResearchArgs(BaseModel):
    """Arguments for Firecrawl research operations."""
    
    query: str = Field(
        description="Search query or research topic"
    )
    
    urls: Optional[List[str]] = Field(
        default=None,
        description="Specific URLs to research (if not provided, will search for relevant URLs)"
    )
    
    max_pages: int = Field(
        default=5,
        description="Maximum number of pages to crawl and analyze"
    )
    
    research_depth: str = Field(
        default="medium",
        description="Research depth: 'shallow' (summaries only), 'medium' (detailed content), 'deep' (comprehensive analysis)"
    )
    
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Types of content to focus on: 'articles', 'papers', 'news', 'documentation', 'blogs'"
    )
    
    save_report: bool = Field(
        default=True,
        description="Whether to save research findings as a report artifact"
    )
    
    include_sources: bool = Field(
        default=True,
        description="Whether to include source URLs and citations in the report"
    )
    
    @validator('research_depth')
    def validate_depth(cls, v):
        """Validate research depth values."""
        if v not in ['shallow', 'medium', 'deep']:
            raise ValueError("research_depth must be 'shallow', 'medium', or 'deep'")
        return v


class FirecrawlResearchTool(Tool):
    """
    Tool for web research using Firecrawl service.
    
    Performs intelligent web research by crawling websites, extracting content,
    and generating comprehensive research reports with proper citations.
    
    Uses real Firecrawl API for web scraping and content extraction.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("hedwig.tools.firecrawl")
        self._firecrawl_client = None
        self._brave_search_api_key = None
        
    def _get_firecrawl_client(self) -> Optional[FirecrawlApp]:
        """Get Firecrawl client instance."""
        if self._firecrawl_client is None:
            if FirecrawlApp is None:
                self.logger.error("firecrawl-py not installed. Install with: pip install firecrawl-py")
                return None
                
            api_key = os.getenv("FIRECRAWL_API_KEY")
            if not api_key:
                self.logger.error("FIRECRAWL_API_KEY not found in environment variables")
                return None
                
            try:
                self._firecrawl_client = FirecrawlApp(api_key=api_key)
                self.logger.info("Initialized Firecrawl client")
            except Exception as e:
                self.logger.error(f"Failed to initialize Firecrawl client: {str(e)}")
                return None
                
        return self._firecrawl_client
        
    def _get_brave_search_key(self) -> Optional[str]:
        """Get Brave Search API key."""
        if self._brave_search_api_key is None:
            self._brave_search_api_key = os.getenv("BRAVE_SEARCH_API_KEY")
            if not self._brave_search_api_key:
                self.logger.warning("BRAVE_SEARCH_API_KEY not found. Web search will be limited.")
        return self._brave_search_api_key
    
    @property
    def args_schema(self):
        return FirecrawlResearchArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.READ_ONLY
    
    @property
    def description(self) -> str:
        return "Conduct web research using intelligent crawling and content extraction"
    
    def _run(self, **kwargs) -> ToolOutput:
        """
        Execute web research using Firecrawl.
        
        Returns:
            ToolOutput with research results and optional report artifacts
        """
        args = FirecrawlResearchArgs(**kwargs)
        
        try:
            self.logger.info(f"Starting web research for query: {args.query}")
            
            # Check if Firecrawl is available
            firecrawl_client = self._get_firecrawl_client()
            if not firecrawl_client:
                return ToolOutput(
                    text_summary="Firecrawl API not available. Please install firecrawl-py and set FIRECRAWL_API_KEY.",
                    artifacts=[],
                    success=False,
                    error_message="Firecrawl API configuration missing"
                )
            
            # Conduct real research using Firecrawl API
            research_results = self._conduct_firecrawl_research(args, firecrawl_client)
            
            artifacts = []
            
            # Save research report if requested
            if args.save_report:
                report_artifact = self._create_research_report(research_results, args)
                if report_artifact:
                    artifacts.append(report_artifact)
            
            # Prepare summary
            summary_parts = [
                f"Completed web research on: {args.query}",
                f"Analyzed {research_results['pages_analyzed']} web pages",
                f"Found {len(research_results['key_findings'])} key findings"
            ]
            
            if args.save_report:
                summary_parts.append("Generated detailed research report")
            
            return ToolOutput(
                text_summary=". ".join(summary_parts),
                artifacts=artifacts,
                success=True,
                metadata={
                    "tool": self.name,
                    "query": args.query,
                    "pages_analyzed": research_results["pages_analyzed"],
                    "research_depth": args.research_depth,
                    "findings_count": len(research_results["key_findings"])
                }
            )
            
        except Exception as e:
            self.logger.error(f"Web research failed: {str(e)}")
            return ToolOutput(
                text_summary=f"Web research failed: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _conduct_firecrawl_research(self, args: FirecrawlResearchArgs, firecrawl_client: FirecrawlApp) -> Dict[str, Any]:
        """
        Conduct real web research using Firecrawl API.
        
        Args:
            args: Research arguments
            firecrawl_client: Initialized Firecrawl client
            
        Returns:
            Dictionary with research results
        """
        try:
            # Step 1: Get URLs to research
            urls_to_research = []
            
            if args.urls:
                # Use provided URLs
                urls_to_research = args.urls[:args.max_pages]
                self.logger.info(f"Using provided URLs: {len(urls_to_research)} URLs")
            else:
                # Search for relevant URLs using Brave Search API
                urls_to_research = self._search_urls_for_query(args.query, args.max_pages)
                self.logger.info(f"Found {len(urls_to_research)} URLs via search")
            
            # Step 2: Scrape content from URLs using Firecrawl
            sources = []
            key_findings = []
            
            for url in urls_to_research:
                try:
                    self.logger.info(f"Scraping URL: {url}")
                    
                    # Use Firecrawl to scrape the URL
                    scraped_data = firecrawl_client.scrape_url(
                        url, 
                        params={
                            'formats': ['markdown', 'html'],
                            'includeTags': ['title', 'meta', 'p', 'h1', 'h2', 'h3'],
                            'excludeTags': ['nav', 'footer', 'script'],
                            'onlyMainContent': True
                        }
                    )
                    
                    if scraped_data and 'markdown' in scraped_data:
                        content = scraped_data['markdown']
                        title = scraped_data.get('metadata', {}).get('title', 'Unknown Title')
                        
                        # Extract key findings from content
                        content_findings = self._extract_key_findings(
                            content, args.query, args.research_depth
                        )
                        key_findings.extend(content_findings)
                        
                        # Add source info
                        sources.append({
                            'url': url,
                            'title': title,
                            'type': self._classify_content_type(url, content),
                            'content_length': len(content),
                            'scraped_at': datetime.now().isoformat()
                        })
                        
                        self.logger.info(f"Successfully scraped {url}: {len(content)} characters")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to scrape {url}: {str(e)}")
                    continue
            
            # Remove duplicate findings
            unique_findings = list(dict.fromkeys(key_findings))
            
            # Limit findings based on research depth
            if args.research_depth == "shallow":
                unique_findings = unique_findings[:3]
            elif args.research_depth == "medium":
                unique_findings = unique_findings[:6]
            # Deep research keeps all findings
            
            return {
                "query": args.query,
                "pages_analyzed": len(sources),
                "key_findings": unique_findings,
                "sources": sources,
                "research_depth": args.research_depth,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Firecrawl research failed: {str(e)}")
            # Fallback to basic results
            return {
                "query": args.query,
                "pages_analyzed": 0,
                "key_findings": [f"Research on '{args.query}' encountered technical difficulties."],
                "sources": [],
                "research_depth": args.research_depth,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _search_urls_for_query(self, query: str, max_results: int = 5) -> List[str]:
        """Search for URLs related to the query using Brave Search API."""
        brave_api_key = self._get_brave_search_key()
        if not brave_api_key:
            # Fallback to some default authoritative sources
            self.logger.warning("No Brave Search API key, using fallback URL generation")
            return self._generate_fallback_urls(query, max_results)
        
        try:
            # Use Brave Search API
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'X-Subscription-Token': brave_api_key
            }
            
            params = {
                'q': query,
                'count': max_results,
                'safesearch': 'moderate',
                'search_lang': 'en',
                'country': 'US'
            }
            
            base_url = os.getenv("BRAVE_SEARCH_BASE_URL", "https://api.search.brave.com/res/v1")
            response = requests.get(
                f"{base_url}/web/search",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                urls = []
                
                # Extract URLs from search results
                for result in data.get('web', {}).get('results', []):
                    url = result.get('url')
                    if url and self._is_valid_research_url(url):
                        urls.append(url)
                        
                self.logger.info(f"Brave Search returned {len(urls)} valid URLs")
                return urls[:max_results]
            else:
                self.logger.error(f"Brave Search API error: {response.status_code}")
                return self._generate_fallback_urls(query, max_results)
                
        except Exception as e:
            self.logger.error(f"Brave Search API failed: {str(e)}")
            return self._generate_fallback_urls(query, max_results)
    
    def _generate_fallback_urls(self, query: str, max_results: int) -> List[str]:
        """Generate fallback URLs for research when search APIs are unavailable."""
        # Use known authoritative sources that might have relevant content
        fallback_domains = [
            "en.wikipedia.org",
            "www.britannica.com", 
            "scholar.google.com",
            "www.nature.com",
            "arxiv.org"
        ]
        
        urls = []
        query_encoded = query.replace(' ', '+')
        
        for domain in fallback_domains[:max_results]:
            if domain == "en.wikipedia.org":
                url = f"https://{domain}/wiki/{query.replace(' ', '_')}"
            elif domain == "scholar.google.com":
                url = f"https://{domain}/scholar?q={query_encoded}"
            elif domain == "arxiv.org":
                url = f"https://{domain}/search/?query={query_encoded}"
            else:
                url = f"https://{domain}/search?q={query_encoded}"
            urls.append(url)
        
        return urls
    
    def _is_valid_research_url(self, url: str) -> bool:
        """Check if URL is suitable for research."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Skip social media and low-quality domains
            skip_domains = [
                'twitter.com', 'facebook.com', 'instagram.com', 'tiktok.com',
                'reddit.com', 'pinterest.com', 'youtube.com'
            ]
            
            return not any(skip in domain for skip in skip_domains)
        except:
            return False
    
    def _extract_key_findings(self, content: str, query: str, depth: str) -> List[str]:
        """Extract key findings from scraped content."""
        findings = []
        
        # Simple content analysis - in production this could use NLP
        sentences = content.split('. ')
        query_terms = query.lower().split()
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check if sentence contains query terms and is substantive
            if (any(term in sentence_lower for term in query_terms) and 
                len(sentence.strip()) > 50 and 
                len(sentence.strip()) < 300):
                
                # Clean up the sentence
                clean_sentence = sentence.strip().replace('\n', ' ').replace('\r', '')
                if clean_sentence and not clean_sentence.endswith('.'):
                    clean_sentence += '.'
                    
                findings.append(clean_sentence)
        
        # Limit findings based on depth
        max_findings = {'shallow': 2, 'medium': 4, 'deep': 8}.get(depth, 4)
        return findings[:max_findings]
    
    def _classify_content_type(self, url: str, content: str) -> str:
        """Classify the type of content based on URL and content analysis."""
        url_lower = url.lower()
        content_lower = content.lower()
        
        if 'wikipedia.org' in url_lower:
            return 'encyclopedia'
        elif 'arxiv.org' in url_lower or 'scholar.google' in url_lower:
            return 'academic'
        elif any(term in url_lower for term in ['news', 'reuters', 'bloomberg', 'bbc']):
            return 'news'
        elif 'blog' in url_lower or 'medium.com' in url_lower:
            return 'blog'
        elif any(term in content_lower for term in ['research', 'study', 'analysis']):
            return 'research'
        elif 'github.com' in url_lower or 'docs.' in url_lower:
            return 'documentation'
        else:
            return 'article'
    
    def _create_research_report(self, research_results: Dict[str, Any], args: FirecrawlResearchArgs) -> Optional[Artifact]:
        """
        Create a research report artifact from the research results.
        
        Args:
            research_results: Results from web research
            args: Original research arguments
            
        Returns:
            Artifact containing the research report
        """
        try:
            # Ensure artifacts directory exists
            config = get_config()
            artifacts_dir = Path(config.data_dir) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in args.query)
            safe_query = '_'.join(safe_query.split())
            filename = f"research_report_{safe_query}_{timestamp}.md"
            file_path = artifacts_dir / filename
            
            # Create report content
            report_lines = [
                f"# Research Report: {args.query}",
                "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Research Depth:** {args.research_depth.title()}",
                f"**Pages Analyzed:** {research_results['pages_analyzed']}",
                "",
                "## Executive Summary",
                "",
                f"This report presents research findings on '{args.query}' based on analysis of {research_results['pages_analyzed']} web sources. "
                f"The research was conducted with {args.research_depth} depth analysis.",
                "",
                "## Key Findings",
                ""
            ]
            
            # Add key findings
            for i, finding in enumerate(research_results["key_findings"], 1):
                report_lines.append(f"{i}. {finding}")
            
            report_lines.extend(["", "## Sources and References", ""])
            
            # Add sources if requested
            if args.include_sources:
                for i, source in enumerate(research_results["sources"], 1):
                    source_type = source.get("type", "webpage").title()
                    report_lines.append(f"{i}. **{source['title']}** ({source_type})")
                    report_lines.append(f"   - URL: {source['url']}")
                    report_lines.append("")
            else:
                report_lines.append("*Source details omitted as requested*")
            
            # Add methodology section
            report_lines.extend([
                "## Research Methodology",
                "",
                f"- **Query:** {args.query}",
                f"- **Research Depth:** {args.research_depth}",
                f"- **Maximum Pages:** {args.max_pages}",
                f"- **Content Types:** {', '.join(args.content_types) if args.content_types else 'All types'}",
                "",
                "This research was conducted using automated web crawling and content extraction "
                "to gather relevant information from authoritative sources.",
                "",
                "---",
                "",
                "*Generated by Hedwig AI Research Assistant*"
            ])
            
            # Write report to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            return Artifact(
                file_path=str(file_path),
                artifact_type="markdown",
                description=f"Research report on: {args.query}",
                metadata={
                    "query": args.query,
                    "research_depth": args.research_depth,
                    "pages_analyzed": research_results["pages_analyzed"],
                    "findings_count": len(research_results["key_findings"]),
                    "file_size": os.path.getsize(file_path)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create research report: {str(e)}")
            return None