"""
Browser Tool for web automation and interaction.

This tool handles web browser automation tasks including navigation,
form filling, data extraction, and screenshot capture.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse, urljoin

from pydantic import BaseModel, Field, validator

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.tools.base import Tool


class BrowserAction(BaseModel):
    """Individual browser action specification."""
    
    action: str = Field(
        description="Action type: 'navigate', 'click', 'type', 'wait', 'screenshot', 'extract'"
    )
    
    target: Optional[str] = Field(
        default=None,
        description="CSS selector, URL, or text to target"
    )
    
    value: Optional[str] = Field(
        default=None,
        description="Value to type or other action-specific data"
    )
    
    wait_time: Optional[float] = Field(
        default=None,
        description="Time to wait in seconds"
    )
    
    @validator('action')
    def validate_action(cls, v):
        """Validate action types."""
        valid_actions = ['navigate', 'click', 'type', 'wait', 'screenshot', 'extract', 'scroll']
        if v not in valid_actions:
            raise ValueError(f"action must be one of: {', '.join(valid_actions)}")
        return v


class BrowserToolArgs(BaseModel):
    """Arguments for browser automation."""
    
    actions: List[BrowserAction] = Field(
        description="List of browser actions to perform in sequence"
    )
    
    headless: bool = Field(
        default=True,
        description="Whether to run browser in headless mode"
    )
    
    timeout: int = Field(
        default=30,
        description="Maximum time to wait for page loads and elements (seconds)"
    )
    
    user_agent: Optional[str] = Field(
        default=None,
        description="Custom user agent string"
    )
    
    save_screenshots: bool = Field(
        default=False,
        description="Whether to save screenshots as artifacts"
    )
    
    extract_data: bool = Field(
        default=True,
        description="Whether to extract and return data from pages"
    )


class BrowserTool(Tool):
    """
    Tool for web browser automation and data extraction.
    
    Provides browser automation capabilities including navigation, interaction,
    and data extraction. Can capture screenshots and extract structured data.
    
    Note: This is a mock implementation. Production use would require
    actual browser automation libraries like Selenium or Playwright.
    """
    
    @property
    def args_schema(self):
        return BrowserToolArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.EXECUTE  # Browser automation can affect external systems
    
    @property
    def description(self) -> str:
        return "Automate web browser interactions including navigation, form filling, and data extraction"
    
    def _run(self, **kwargs) -> ToolOutput:
        """
        Execute browser automation tasks.
        
        Returns:
            ToolOutput with automation results and optional artifacts
        """
        args = BrowserToolArgs(**kwargs)
        
        try:
            self.logger.info(f"Starting browser automation with {len(args.actions)} actions")
            
            # Mock implementation - in production this would use actual browser automation
            automation_results = self._execute_mock_automation(args)
            
            artifacts = []
            
            # Save screenshots if requested
            if args.save_screenshots and automation_results.get("screenshots"):
                for screenshot_data in automation_results["screenshots"]:
                    artifact = self._create_screenshot_artifact(screenshot_data)
                    if artifact:
                        artifacts.append(artifact)
            
            # Save extracted data if available
            if args.extract_data and automation_results.get("extracted_data"):
                data_artifact = self._create_data_artifact(automation_results["extracted_data"])
                if data_artifact:
                    artifacts.append(data_artifact)
            
            # Prepare summary
            summary_parts = [
                f"Completed {len(args.actions)} browser actions",
                f"Visited {automation_results.get('pages_visited', 0)} page(s)"
            ]
            
            if automation_results.get("data_extracted"):
                summary_parts.append(f"Extracted {len(automation_results['data_extracted'])} data items")
            
            if args.save_screenshots:
                screenshot_count = len(automation_results.get("screenshots", []))
                summary_parts.append(f"Captured {screenshot_count} screenshot(s)")
            
            return ToolOutput(
                text_summary=". ".join(summary_parts),
                artifacts=artifacts,
                success=True,
                metadata={
                    "tool": self.name,
                    "actions_executed": len(args.actions),
                    "pages_visited": automation_results.get("pages_visited", 0),
                    "execution_time": automation_results.get("execution_time", 0),
                    "data_extracted": automation_results.get("data_extracted", [])
                }
            )
            
        except Exception as e:
            self.logger.error(f"Browser automation failed: {str(e)}")
            return ToolOutput(
                text_summary=f"Browser automation failed: {str(e)}",
                artifacts=[],
                success=False,
                error_message=str(e)
            )
    
    def _execute_mock_automation(self, args: BrowserToolArgs) -> Dict[str, Any]:
        """
        Execute mock browser automation (placeholder for actual browser automation).
        
        Args:
            args: Browser automation arguments
            
        Returns:
            Dictionary with mock automation results
        """
        start_time = time.time()
        
        results = {
            "actions_executed": [],
            "pages_visited": 0,
            "screenshots": [],
            "data_extracted": [],
            "execution_time": 0
        }
        
        current_url = None
        
        for i, action in enumerate(args.actions):
            action_result = {
                "action": action.action,
                "target": action.target,
                "value": action.value,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            if action.action == "navigate":
                current_url = action.target
                results["pages_visited"] += 1
                action_result["url"] = current_url
                
                # Mock page load time
                time.sleep(0.1)
                
            elif action.action == "click":
                # Mock click action
                action_result["element"] = action.target
                time.sleep(0.05)
                
            elif action.action == "type":
                # Mock typing action
                action_result["text_entered"] = action.value
                action_result["element"] = action.target
                time.sleep(0.05)
                
            elif action.action == "wait":
                # Mock wait
                wait_time = action.wait_time or 1.0
                time.sleep(min(wait_time, 0.1))  # Simulate but don't actually wait
                action_result["wait_time"] = wait_time
                
            elif action.action == "screenshot":
                # Mock screenshot
                screenshot_data = {
                    "filename": f"screenshot_{i}_{int(time.time())}.png",
                    "url": current_url,
                    "timestamp": datetime.now().isoformat(),
                    "mock_data": True
                }
                results["screenshots"].append(screenshot_data)
                action_result["screenshot"] = screenshot_data["filename"]
                
            elif action.action == "extract":
                # Mock data extraction
                extracted_items = self._generate_mock_extracted_data(current_url, action.target)
                results["data_extracted"].extend(extracted_items)
                action_result["extracted_count"] = len(extracted_items)
                
            elif action.action == "scroll":
                # Mock scroll action
                action_result["scroll_target"] = action.target or "page_end"
                time.sleep(0.05)
            
            results["actions_executed"].append(action_result)
        
        results["execution_time"] = time.time() - start_time
        return results
    
    def _generate_mock_extracted_data(self, url: Optional[str], selector: Optional[str]) -> List[Dict[str, Any]]:
        """
        Generate mock extracted data based on URL and selector.
        
        Args:
            url: Current page URL
            selector: CSS selector for extraction
            
        Returns:
            List of mock extracted data items
        """
        if not url:
            return []
        
        domain = urlparse(url).netloc if url else "example.com"
        
        # Generate mock data based on common extraction patterns
        mock_data = []
        
        if "news" in url or "article" in url:
            mock_data = [
                {"type": "headline", "text": "Breaking: Technology Advances Continue", "url": url},
                {"type": "author", "text": "Tech Reporter", "url": url},
                {"type": "date", "text": "2024-01-15", "url": url},
                {"type": "content", "text": "Recent developments show significant progress...", "url": url}
            ]
        elif "product" in url or "shop" in url:
            mock_data = [
                {"type": "product_name", "text": "Sample Product", "url": url},
                {"type": "price", "text": "$99.99", "url": url},
                {"type": "rating", "text": "4.5/5", "url": url},
                {"type": "description", "text": "High-quality product with excellent features", "url": url}
            ]
        elif "contact" in url or "about" in url:
            mock_data = [
                {"type": "company_name", "text": f"{domain.split('.')[0].title()} Company", "url": url},
                {"type": "email", "text": f"contact@{domain}", "url": url},
                {"type": "phone", "text": "+1-555-0123", "url": url},
                {"type": "address", "text": "123 Main St, City, State", "url": url}
            ]
        else:
            # Generic content extraction
            mock_data = [
                {"type": "title", "text": f"Page Title from {domain}", "url": url},
                {"type": "text", "text": "Sample text content extracted from the page", "url": url},
                {"type": "link", "text": f"https://{domain}/related-page", "url": url}
            ]
        
        # Filter based on selector if provided
        if selector:
            if "title" in selector or "h1" in selector:
                mock_data = [item for item in mock_data if item["type"] in ["title", "headline"]]
            elif "link" in selector or "a" in selector:
                mock_data = [item for item in mock_data if item["type"] == "link"]
            elif "price" in selector:
                mock_data = [item for item in mock_data if item["type"] == "price"]
        
        return mock_data
    
    def _create_screenshot_artifact(self, screenshot_data: Dict[str, Any]) -> Optional[Artifact]:
        """
        Create a mock screenshot artifact.
        
        Args:
            screenshot_data: Screenshot metadata
            
        Returns:
            Artifact for the screenshot
        """
        try:
            # Ensure artifacts directory exists
            config = get_config()
            artifacts_dir = Path(config.data_dir) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Create mock screenshot file
            filename = screenshot_data["filename"]
            file_path = artifacts_dir / filename
            
            # Create a mock PNG file (minimal valid PNG header)
            png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            
            with open(file_path, 'wb') as f:
                f.write(png_header)
            
            return Artifact(
                file_path=str(file_path),
                artifact_type="other",
                description=f"Browser screenshot: {screenshot_data.get('url', 'Unknown page')}",
                metadata={
                    "url": screenshot_data.get("url"),
                    "timestamp": screenshot_data.get("timestamp"),
                    "file_size": os.path.getsize(file_path),
                    "is_mock": True
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create screenshot artifact: {str(e)}")
            return None
    
    def _create_data_artifact(self, extracted_data: List[Dict[str, Any]]) -> Optional[Artifact]:
        """
        Create an artifact containing extracted data.
        
        Args:
            extracted_data: List of extracted data items
            
        Returns:
            Artifact containing the extracted data
        """
        try:
            # Ensure artifacts directory exists
            config = get_config()
            artifacts_dir = Path(config.data_dir) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"browser_extracted_data_{timestamp}.json"
            file_path = artifacts_dir / filename
            
            # Prepare data for JSON serialization
            output_data = {
                "extraction_timestamp": datetime.now().isoformat(),
                "total_items": len(extracted_data),
                "data": extracted_data
            }
            
            # Write data to JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            return Artifact(
                file_path=str(file_path),
                artifact_type="other",
                description=f"Browser extracted data ({len(extracted_data)} items)",
                metadata={
                    "data_items": len(extracted_data),
                    "extraction_timestamp": output_data["extraction_timestamp"],
                    "file_size": os.path.getsize(file_path)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create data artifact: {str(e)}")
            return None