"""
Verification script for AgentBeats implementation.

This script checks that all components can be imported and basic
functionality works before running a full assessment.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required = [
        ('a2a_sdk', 'a2a-sdk'),
        ('aiohttp', 'aiohttp'),
        ('datasets', 'datasets'),
        ('openai', 'openai'),
        ('anthropic', 'anthropic'),
        ('google.generativeai', 'google-generativeai')
    ]
    
    missing = []
    for module, package in required:
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (run: pip install {package})")
            missing.append(package)
    
    return len(missing) == 0


def check_api_keys():
    """Check if API keys are configured."""
    print("\n🔑 Checking API keys...")
    
    keys = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY')
    }
    
    all_set = True
    for key_name, key_value in keys.items():
        if key_value:
            print(f"  ✅ {key_name} is set")
        else:
            print(f"  ⚠️  {key_name} not set (required for {key_name.split('_')[0]} agent)")
            all_set = False
    
    return all_set


def check_imports():
    """Check if AgentBeats components can be imported."""
    print("\n📦 Checking AgentBeats imports...")
    
    try:
        from src.green_agent import GreenAgent
        print("  ✅ Green agent imports OK")
    except Exception as e:
        print(f"  ❌ Green agent import failed: {e}")
        return False
    
    try:
        from src.dataset_loader import DatasetLoader
        print("  ✅ Dataset loader imports OK")
    except Exception as e:
        print(f"  ❌ Dataset loader import failed: {e}")
        return False
    
    try:
        from src.agents.gpt_agent import GPTAgent
        print("  ✅ Existing agents import OK")
    except Exception as e:
        print(f"  ❌ Existing agents import failed: {e}")
        return False
    
    return True


def check_agent_creation():
    """Test agent instantiation."""
    print("\n🤖 Testing agent creation...")
    
    try:
        from src.green_agent import GreenAgent
        green = GreenAgent("TestGreenAgent")
        print(f"  ✅ Green agent created: {green.agent_name}")
    except Exception as e:
        print(f"  ❌ Green agent creation failed: {e}")
        return False
    
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("🧪 AgentBeats Implementation Verification")
    print("=" * 60)
    
    results = []
    
    # Check dependencies
    results.append(("Dependencies", check_dependencies()))
    
    # Check API keys
    api_keys_ok = check_api_keys()
    results.append(("API Keys", api_keys_ok))
    
    # Check imports
    imports_ok = check_imports()
    results.append(("Imports", imports_ok))
    
    # Check agent creation
    if imports_ok:
        agents_ok = check_agent_creation()
        results.append(("Agent Creation", agents_ok))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Verification Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ All checks passed!")
        print("\n🚀 Ready to run assessment:")
        print("   python src/launcher.py --agent gpt --samples 3")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\n📝 Common fixes:")
        print("   - Install dependencies: pip install -r requirements.txt")
        print("   - Set API keys in .env or environment variables")
        print("   - Check Python path: export PYTHONPATH=$(pwd):$PYTHONPATH")
    
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

