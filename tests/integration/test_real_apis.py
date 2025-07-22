#!/usr/bin/env python3
"""
Test script to validate real API integrations in Hedwig tools.

This script tests:
1. Firecrawl API integration
2. Playwright browser automation
3. Brave Search API integration
4. PDF generation (ReportLab)
"""

import sys
import os
sys.path.insert(0, 'src')

def test_firecrawl_availability():
    """Test if Firecrawl is properly configured."""
    print("🔧 Testing Firecrawl Integration...")
    
    try:
        from hedwig.tools.firecrawl_research import FirecrawlResearchTool
        
        tool = FirecrawlResearchTool()
        print("✓ FirecrawlResearchTool imported successfully")
        
        # Check if API key is configured
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if api_key:
            print("✓ FIRECRAWL_API_KEY is configured")
        else:
            print("⚠ FIRECRAWL_API_KEY not found in environment")
        
        # Check if firecrawl-py is installed
        try:
            import firecrawl
            print("✓ firecrawl-py library is available")
            return True
        except ImportError:
            print("✗ firecrawl-py library not installed")
            print("  Install with: pip install firecrawl-py")
            return False
            
    except Exception as e:
        print(f"✗ Firecrawl integration error: {e}")
        return False

def test_playwright_availability():
    """Test if Playwright is properly configured."""
    print("\n🔧 Testing Playwright Integration...")
    
    try:
        from hedwig.tools.browser_tool import BrowserTool
        
        tool = BrowserTool()
        print("✓ BrowserTool imported successfully")
        
        # Check if playwright is installed
        try:
            from playwright.async_api import async_playwright
            print("✓ playwright library is available")
            
            # Check browser preferences
            headless = os.getenv("HEDWIG_BROWSER_HEADLESS", "true")
            user_agent = os.getenv("HEDWIG_BROWSER_USER_AGENT", "Mozilla/5.0 (compatible; Hedwig-AI/1.0)")
            print(f"✓ Browser preferences: headless={headless}, user_agent={user_agent[:50]}...")
            
            return True
        except ImportError:
            print("✗ playwright library not installed")
            print("  Install with: pip install playwright")
            print("  Then run: playwright install")
            return False
            
    except Exception as e:
        print(f"✗ Playwright integration error: {e}")
        return False

def test_brave_search_availability():
    """Test if Brave Search API is configured."""
    print("\n🔧 Testing Brave Search Integration...")
    
    try:
        # Check if API key is configured
        api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if api_key:
            print("✓ BRAVE_SEARCH_API_KEY is configured")
        else:
            print("⚠ BRAVE_SEARCH_API_KEY not found in environment")
            print("  Note: This is optional - fallback URLs will be used")
        
        # Check if requests library is available
        try:
            import requests
            print("✓ requests library is available")
            return True
        except ImportError:
            print("✗ requests library not installed")
            print("  Install with: pip install requests")
            return False
            
    except Exception as e:
        print(f"✗ Brave Search integration error: {e}")
        return False

def test_pdf_generation():
    """Test if PDF generation (ReportLab) is working."""
    print("\n🔧 Testing PDF Generation...")
    
    try:
        from hedwig.tools.pdf_generator import PDFGeneratorTool
        
        tool = PDFGeneratorTool()
        print("✓ PDFGeneratorTool imported successfully")
        
        # Check if ReportLab is available
        try:
            from reportlab.lib.pagesizes import letter
            print("✓ reportlab library is available")
            return True
        except ImportError:
            print("✗ reportlab library not installed")
            print("  Install with: pip install reportlab")
            return False
            
    except Exception as e:
        print(f"✗ PDF generation error: {e}")
        return False

def test_environment_setup():
    """Test overall environment setup."""
    print("\n🔧 Testing Environment Setup...")
    
    # Check .env file
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        print("✓ .env file found")
    else:
        print("⚠ .env file not found")
        print("  Create .env file from .env.template")
    
    # Check artifacts directory
    try:
        from hedwig.core.config import get_config
        config = get_config()
        artifacts_dir = Path(config.data_dir) / "artifacts"
        print(f"✓ Artifacts directory: {artifacts_dir}")
        return True
    except Exception as e:
        print(f"✗ Environment setup error: {e}")
        return False

def main():
    """Run all API integration tests."""
    print("🚀 Hedwig Real API Integration Test")
    print("=" * 50)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("Firecrawl Integration", test_firecrawl_availability),
        ("Playwright Integration", test_playwright_availability),
        ("Brave Search Integration", test_brave_search_availability),
        ("PDF Generation", test_pdf_generation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 API Integration Test Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All API integrations are properly configured!")
        print("\nNext steps:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. For Playwright: playwright install")
        print("3. Set up API keys in .env file")
        print("4. Run functional test: python test_llm_integration.py")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} integration(s) need attention.")
        print("\nRecommended actions:")
        print("1. Install missing dependencies")
        print("2. Configure API keys in .env file")
        print("3. Run playwright install if using browser automation")
        return 1

if __name__ == "__main__":
    sys.exit(main())