#!/usr/bin/env python3
"""
Simple test to verify the virtual environment and dependencies are working.
"""

import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

def test_imports():
    """Test critical imports."""
    tests = []
    
    # Test pydantic
    try:
        import pydantic
        tests.append(("✓", "pydantic", pydantic.__version__))
    except ImportError as e:
        tests.append(("✗", "pydantic", f"ImportError: {e}"))
    
    # Test openai
    try:
        import openai
        tests.append(("✓", "openai", openai.__version__))
    except ImportError as e:
        tests.append(("✗", "openai", f"ImportError: {e}"))
    
    # Test firecrawl
    try:
        import firecrawl
        tests.append(("✓", "firecrawl-py", "imported successfully"))
    except ImportError as e:
        tests.append(("✗", "firecrawl-py", f"ImportError: {e}"))
    
    # Test playwright
    try:
        from playwright.async_api import async_playwright
        tests.append(("✓", "playwright", "imported successfully"))
    except ImportError as e:
        tests.append(("✗", "playwright", f"ImportError: {e}"))
    
    # Test reportlab
    try:
        import reportlab
        tests.append(("✓", "reportlab", reportlab.__version__))
    except ImportError as e:
        tests.append(("✗", "reportlab", f"ImportError: {e}"))
    
    # Test requests
    try:
        import requests
        tests.append(("✓", "requests", requests.__version__))
    except ImportError as e:
        tests.append(("✗", "requests", f"ImportError: {e}"))
    
    return tests

def main():
    print("🔧 Testing Virtual Environment Setup")
    print("=" * 50)
    
    tests = test_imports()
    
    print("\nDependency Tests:")
    passed = 0
    for status, package, version in tests:
        print(f"{status} {package}: {version}")
        if status == "✓":
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} dependencies available")
    
    if passed == len(tests):
        print("\n🎉 All dependencies are properly installed!")
        print("\nYou can now configure API keys in .env and run:")
        print("• python test_llm_integration.py")
        print("• Test individual tools through the Hedwig system")
        return 0
    else:
        print(f"\n⚠️  {len(tests) - passed} dependencies missing or have issues.")
        print("Make sure you're running this from the activated virtual environment:")
        print("  source venv/bin/activate")
        print("  python test_setup.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())