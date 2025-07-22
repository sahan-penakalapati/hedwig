"""
Browser Tool for web automation and interaction.

This tool handles web browser automation tasks including navigation,
form filling, data extraction, and screenshot capture.
"""

import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse, urljoin

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    async_playwright = None
    Browser = None
    Page = None

from pydantic import BaseModel, Field, validator

from hedwig.core.models import RiskTier, ToolOutput, Artifact
from hedwig.core.config import get_config
from hedwig.core.logging_config import get_logger
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
    
    Uses Playwright for real browser automation.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("hedwig.tools.browser")
        self._browser = None
        self._page = None
    
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
            
            # Check if Playwright is available
            if async_playwright is None:
                return ToolOutput(
                    text_summary="Playwright not available. Please install with: pip install playwright",
                    artifacts=[],
                    success=False,
                    error_message="Playwright library not found"
                )
            
            # Execute real browser automation using Playwright
            automation_results = asyncio.run(self._execute_playwright_automation(args))
            
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
    
    async def _execute_playwright_automation(self, args: BrowserToolArgs) -> Dict[str, Any]:
        """
        Execute real browser automation using Playwright.
        
        Args:
            args: Browser automation arguments
            
        Returns:
            Dictionary with automation results
        """
        start_time = time.time()
        
        results = {
            "actions_executed": [],
            "pages_visited": 0,
            "screenshots": [],
            "data_extracted": [],
            "execution_time": 0
        }
        
        try:
            async with async_playwright() as p:
                # Launch browser
                browser_type = p.chromium  # Can be changed to firefox or webkit
                
                # Get browser preferences from environment
                headless = args.headless if args.headless is not None else os.getenv("HEDWIG_BROWSER_HEADLESS", "true").lower() == "true"
                user_agent = args.user_agent or os.getenv("HEDWIG_BROWSER_USER_AGENT", "Mozilla/5.0 (compatible; Hedwig-AI/1.0)")
                
                self.logger.info(f"Launching browser (headless={headless})")
                browser = await browser_type.launch(
                    headless=headless,
                    timeout=args.timeout * 1000  # Playwright expects milliseconds
                )
                
                # Create new page
                page = await browser.new_page(
                    user_agent=user_agent,
                    viewport={'width': 1280, 'height': 720}
                )
                
                # Set default timeout
                page.set_default_timeout(args.timeout * 1000)
                
                current_url = None
                
                for i, action in enumerate(args.actions):
                    action_result = {
                        "action": action.action,
                        "target": action.target,
                        "value": action.value,
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    try:
                        if action.action == "navigate":
                            self.logger.info(f"Navigating to: {action.target}")
                            await page.goto(action.target, wait_until="domcontentloaded")
                            current_url = action.target
                            results["pages_visited"] += 1
                            action_result["url"] = current_url
                            
                        elif action.action == "click":
                            self.logger.info(f"Clicking element: {action.target}")
                            await page.click(action.target)
                            action_result["element"] = action.target
                            
                        elif action.action == "type":
                            self.logger.info(f"Typing in element: {action.target}")
                            await page.fill(action.target, action.value or "")
                            action_result["text_entered"] = action.value
                            action_result["element"] = action.target
                            
                        elif action.action == "wait":
                            wait_time = action.wait_time or 1.0
                            self.logger.info(f"Waiting for {wait_time} seconds")
                            await page.wait_for_timeout(int(wait_time * 1000))
                            action_result["wait_time"] = wait_time
                            
                        elif action.action == "screenshot":
                            self.logger.info("Taking screenshot")
                            screenshot_data = await self._take_screenshot(page, i, current_url)
                            if screenshot_data:
                                results["screenshots"].append(screenshot_data)
                                action_result["screenshot"] = screenshot_data["filename"]
                            
                        elif action.action == "extract":
                            self.logger.info(f"Extracting data with selector: {action.target}")
                            extracted_items = await self._extract_data_from_page(page, action.target, current_url)
                            results["data_extracted"].extend(extracted_items)
                            action_result["extracted_count"] = len(extracted_items)
                            
                        elif action.action == "scroll":
                            if action.target == "page_end" or not action.target:
                                self.logger.info("Scrolling to page end")
                                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            else:
                                self.logger.info(f"Scrolling to element: {action.target}")
                                await page.scroll_into_view_if_needed(action.target)
                            action_result["scroll_target"] = action.target or "page_end"
                        
                    except Exception as e:
                        self.logger.error(f"Action {action.action} failed: {str(e)}")
                        action_result["success"] = False
                        action_result["error"] = str(e)
                    
                    results["actions_executed"].append(action_result)
                
                # Close browser
                await browser.close()
                
        except Exception as e:
            self.logger.error(f"Browser automation failed: {str(e)}")
            results["error"] = str(e)
        
        results["execution_time"] = time.time() - start_time
        return results
    
    async def _take_screenshot(self, page: Page, index: int, current_url: Optional[str]) -> Optional[Dict[str, Any]]:
        """Take a screenshot using Playwright."""
        try:
            # Ensure artifacts directory exists
            config = get_config()
            artifacts_dir = Path(config.data_dir) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = int(time.time())
            filename = f"screenshot_{index}_{timestamp}.png"
            file_path = artifacts_dir / filename
            
            # Take screenshot
            await page.screenshot(path=str(file_path), full_page=True)
            
            screenshot_data = {
                "filename": filename,
                "url": current_url,
                "timestamp": datetime.now().isoformat(),
                "file_path": str(file_path),
                "file_size": os.path.getsize(file_path)
            }
            
            self.logger.info(f"Screenshot saved: {filename}")
            return screenshot_data
            
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {str(e)}")
            return None
    
    async def _extract_data_from_page(self, page: Page, selector: Optional[str], current_url: Optional[str]) -> List[Dict[str, Any]]:
        """Extract data from page using Playwright."""
        try:
            extracted_data = []
            
            if selector:
                # Extract data using specific selector
                elements = await page.query_selector_all(selector)
                
                for i, element in enumerate(elements):
                    try:
                        # Get text content
                        text = await element.inner_text()
                        
                        # Get attributes
                        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                        
                        item = {
                            "type": self._classify_element_type(tag_name, selector),
                            "text": text.strip() if text else "",
                            "url": current_url,
                            "index": i,
                            "selector": selector,
                            "tag": tag_name
                        }
                        
                        # Get href for links
                        if tag_name == "a":
                            href = await element.get_attribute("href")
                            if href:
                                # Convert relative URLs to absolute
                                if current_url and not href.startswith(('http://', 'https://')):
                                    href = urljoin(current_url, href)
                                item["href"] = href
                        
                        # Get src for images
                        if tag_name == "img":
                            src = await element.get_attribute("src")
                            if src:
                                if current_url and not src.startswith(('http://', 'https://')):
                                    src = urljoin(current_url, src)
                                item["src"] = src
                            
                            alt = await element.get_attribute("alt")
                            if alt:
                                item["alt"] = alt
                        
                        if item["text"] or item.get("href") or item.get("src"):
                            extracted_data.append(item)
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to extract from element {i}: {str(e)}")
                        continue
            else:
                # Extract common page elements when no selector is provided
                common_selectors = {
                    "title": "title",
                    "heading": "h1, h2, h3",
                    "paragraph": "p",
                    "link": "a[href]",
                    "image": "img[src]"
                }
                
                for data_type, css_selector in common_selectors.items():
                    elements = await page.query_selector_all(css_selector)
                    
                    for i, element in enumerate(elements[:5]):  # Limit to 5 per type
                        try:
                            text = await element.inner_text()
                            if text and text.strip():
                                item = {
                                    "type": data_type,
                                    "text": text.strip()[:200],  # Limit text length
                                    "url": current_url,
                                    "index": i
                                }
                                
                                # Add href for links
                                if data_type == "link":
                                    href = await element.get_attribute("href")
                                    if href and current_url:
                                        if not href.startswith(('http://', 'https://')):
                                            href = urljoin(current_url, href)
                                        item["href"] = href
                                
                                extracted_data.append(item)
                                
                        except Exception as e:
                            continue
            
            self.logger.info(f"Extracted {len(extracted_data)} data items")
            return extracted_data
            
        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            return []
    
    def _classify_element_type(self, tag_name: str, selector: str) -> str:
        """Classify the type of extracted element."""
        if "title" in selector.lower() or tag_name in ["title", "h1", "h2", "h3"]:
            return "title"
        elif "link" in selector.lower() or tag_name == "a":
            return "link"
        elif "img" in selector.lower() or tag_name == "img":
            return "image"
        elif "price" in selector.lower() or "$" in selector:
            return "price"
        elif "button" in selector.lower() or tag_name == "button":
            return "button"
        elif tag_name == "p":
            return "paragraph"
        else:
            return "text"
    
    
    def _create_screenshot_artifact(self, screenshot_data: Dict[str, Any]) -> Optional[Artifact]:
        """
        Create a screenshot artifact from real screenshot data.
        
        Args:
            screenshot_data: Screenshot metadata from Playwright
            
        Returns:
            Artifact for the screenshot
        """
        try:
            file_path = screenshot_data.get("file_path")
            if not file_path or not os.path.exists(file_path):
                self.logger.error("Screenshot file not found")
                return None
            
            return Artifact(
                file_path=file_path,
                artifact_type="other",
                description=f"Browser screenshot: {screenshot_data.get('url', 'Unknown page')}",
                metadata={
                    "url": screenshot_data.get("url"),
                    "timestamp": screenshot_data.get("timestamp"),
                    "file_size": screenshot_data.get("file_size", 0),
                    "filename": screenshot_data.get("filename"),
                    "is_real_screenshot": True
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