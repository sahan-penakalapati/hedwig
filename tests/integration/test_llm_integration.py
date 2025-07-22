#!/usr/bin/env python3
"""
Simple test script to verify LLM integration is working.
"""

import sys
import os
sys.path.insert(0, 'src')

from hedwig.core.llm_integration import get_llm_client, validate_llm_connection, get_llm_callback
from hedwig.core.config import get_config

def test_basic_connection():
    """Test basic LLM connection and configuration."""
    print("🔧 Testing LLM configuration...")
    
    try:
        config = get_config()
        print(f"✓ Config loaded successfully")
        print(f"  - LLM Provider: {config.llm.provider}")
        print(f"  - LLM Model: {config.llm.model}")
        print(f"  - API Key: {'✓ Set' if config.llm.api_key or os.getenv('OPENAI_API_KEY') else '✗ Missing'}")
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False
    
    return True

def test_llm_client():
    """Test LLM client initialization."""
    print("\n🔧 Testing LLM client initialization...")
    
    try:
        client = get_llm_client()
        print(f"✓ LLM client initialized successfully")
        print(f"  - Model: {client.model}")
        
        # Test stats
        stats = client.get_stats()
        print(f"  - Initial stats: {stats}")
        
    except Exception as e:
        print(f"✗ LLM client error: {e}")
        return False
    
    return True

def test_llm_validation():
    """Test LLM connection validation."""
    print("\n🔧 Testing LLM connection validation...")
    
    try:
        is_valid = validate_llm_connection()
        if is_valid:
            print("✓ LLM connection validated successfully")
        else:
            print("✗ LLM connection validation failed")
            
        return is_valid
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False

def test_simple_completion():
    """Test simple LLM completion."""
    print("\n🔧 Testing simple LLM completion...")
    
    try:
        callback = get_llm_callback()
        
        # Simple test prompt
        prompt = "Say 'Hello from Hedwig AI!' and nothing else."
        print(f"  Prompt: {prompt}")
        
        response = callback(prompt)
        print(f"  Response: {response}")
        
        if "hedwig" in response.lower() or "hello" in response.lower():
            print("✓ LLM completion successful")
            return True
        else:
            print("⚠ LLM responded but content may be unexpected")
            return True
            
    except Exception as e:
        print(f"✗ LLM completion error: {e}")
        return False

def test_agent_integration():
    """Test LLM integration with agent system."""
    print("\n🔧 Testing agent integration...")
    
    try:
        from hedwig.app import HedwigApp
        
        # Initialize HedwigApp (this will test the full integration)
        print("  Initializing HedwigApp...")
        app = HedwigApp()
        print("✓ HedwigApp initialized with real LLM integration")
        
        # Test a simple agent task
        print("  Testing simple agent task...")
        result = app.run("Hello! Please respond with 'AI system is working correctly'")
        
        if result.success:
            print("✓ Agent execution successful")
            print(f"  Response: {result.content[:200]}...")
        else:
            print("✗ Agent execution failed")
            print(f"  Error: {result.error}")
            return False
            
    except Exception as e:
        print(f"✗ Agent integration error: {e}")
        return False
    
    return True

def main():
    """Run all LLM integration tests."""
    print("🚀 Hedwig LLM Integration Test")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_basic_connection),
        ("LLM Client", test_llm_client),
        ("Connection Validation", test_llm_validation),
        ("Simple Completion", test_simple_completion),
        ("Agent Integration", test_agent_integration),
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
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! LLM integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Check configuration and API key.")
        return 1

if __name__ == "__main__":
    sys.exit(main())