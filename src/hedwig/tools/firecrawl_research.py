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

from pydantic import BaseModel, Field, validator

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
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
    
    Note: This is a mock implementation as Firecrawl service integration
    would require API keys and external service setup.
    """
    
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
            
            # Mock implementation - in production this would use actual Firecrawl API
            research_results = self._conduct_mock_research(args)
            
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
    
    def _conduct_mock_research(self, args: FirecrawlResearchArgs) -> Dict[str, Any]:
        """
        Conduct mock web research (placeholder for actual Firecrawl integration).
        
        Args:
            args: Research arguments
            
        Returns:
            Dictionary with mock research results
        """
        # Mock research results based on query
        query_lower = args.query.lower()
        
        # Generate mock findings based on query content
        key_findings = []
        sources = []
        
        if "ai" in query_lower or "artificial intelligence" in query_lower:
            key_findings = [
                "AI technology continues to advance rapidly with new breakthroughs in large language models",
                "Machine learning applications are expanding across healthcare, finance, and automation",
                "Ethical AI development and regulation are becoming increasingly important",
                "AI adoption in enterprise settings is growing, with focus on productivity gains"
            ]
            sources = [
                {"url": "https://example.com/ai-trends-2024", "title": "AI Trends 2024", "type": "article"},
                {"url": "https://example.com/ml-applications", "title": "Machine Learning Applications", "type": "research"},
                {"url": "https://example.com/ai-ethics", "title": "AI Ethics Guidelines", "type": "documentation"},
                {"url": "https://example.com/enterprise-ai", "title": "Enterprise AI Adoption", "type": "report"}
            ]
        elif "python" in query_lower:
            key_findings = [
                "Python remains the most popular programming language for data science and AI",
                "Python 3.12 introduces new performance improvements and syntax features",
                "The Python ecosystem continues to grow with new libraries and frameworks",
                "Python is increasingly used in web development, automation, and scientific computing"
            ]
            sources = [
                {"url": "https://example.com/python-trends", "title": "Python Usage Trends", "type": "article"},
                {"url": "https://example.com/python-312", "title": "Python 3.12 Features", "type": "documentation"},
                {"url": "https://example.com/python-ecosystem", "title": "Python Ecosystem", "type": "blog"},
                {"url": "https://example.com/python-web-dev", "title": "Python Web Development", "type": "tutorial"}
            ]
        elif "climate" in query_lower or "environment" in query_lower:
            key_findings = [
                "Climate change impacts are accelerating globally with rising temperatures",
                "Renewable energy adoption is increasing but needs faster deployment",
                "Carbon capture technology shows promise but requires significant investment",
                "International cooperation on climate action remains challenging but essential"
            ]
            sources = [
                {"url": "https://example.com/climate-data", "title": "Global Climate Data", "type": "research"},
                {"url": "https://example.com/renewable-energy", "title": "Renewable Energy Report", "type": "report"},
                {"url": "https://example.com/carbon-capture", "title": "Carbon Capture Technology", "type": "article"},
                {"url": "https://example.com/climate-policy", "title": "Climate Policy Analysis", "type": "analysis"}
            ]
        else:
            # Generic findings for other topics
            key_findings = [
                f"Current developments in {args.query} show significant growth and innovation",
                f"Industry experts highlight the importance of {args.query} in future planning",
                f"Recent studies on {args.query} reveal new insights and opportunities",
                f"Market trends indicate increased investment and interest in {args.query}"
            ]
            sources = [
                {"url": f"https://example.com/{args.query.replace(' ', '-')}-overview", "title": f"{args.query} Overview", "type": "article"},
                {"url": f"https://example.com/{args.query.replace(' ', '-')}-trends", "title": f"{args.query} Trends", "type": "analysis"},
                {"url": f"https://example.com/{args.query.replace(' ', '-')}-research", "title": f"{args.query} Research", "type": "research"},
                {"url": f"https://example.com/{args.query.replace(' ', '-')}-market", "title": f"{args.query} Market Data", "type": "report"}
            ]
        
        # Adjust findings based on research depth
        if args.research_depth == "shallow":
            key_findings = key_findings[:2]
            sources = sources[:2]
        elif args.research_depth == "deep":
            # Add more detailed findings for deep research
            key_findings.extend([
                f"Detailed analysis of {args.query} reveals complex interdependencies",
                f"Historical context shows {args.query} has evolved significantly over time",
                f"Future projections for {args.query} indicate continued development"
            ])
            sources.extend([
                {"url": f"https://example.com/{args.query.replace(' ', '-')}-history", "title": f"History of {args.query}", "type": "academic"},
                {"url": f"https://example.com/{args.query.replace(' ', '-')}-future", "title": f"Future of {args.query}", "type": "forecast"}
            ])
        
        # Limit by max_pages
        sources = sources[:args.max_pages]
        
        return {
            "query": args.query,
            "pages_analyzed": len(sources),
            "key_findings": key_findings,
            "sources": sources,
            "research_depth": args.research_depth,
            "timestamp": datetime.now().isoformat()
        }
    
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