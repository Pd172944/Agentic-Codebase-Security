#!/bin/bash
# Quick test script for AgentBeats implementation

echo "======================================================"
echo "🧪 Testing AgentBeats Green/White Agent Implementation"
echo "======================================================"
echo ""

# Check Python version
echo "1. Checking Python version..."
python3 --version || python --version

# Check dependencies
echo ""
echo "2. Checking dependencies..."
python3 -c "import a2a_sdk; print('✅ a2a-sdk installed')" 2>/dev/null || echo "❌ a2a-sdk not installed (run: pip install a2a-sdk)"
python3 -c "import aiohttp; print('✅ aiohttp installed')" 2>/dev/null || echo "❌ aiohttp not installed (run: pip install aiohttp)"

# Check API keys
echo ""
echo "3. Checking API keys..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
else
    echo "✅ OPENAI_API_KEY set"
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set"
else
    echo "✅ ANTHROPIC_API_KEY set"
fi

# Test imports
echo ""
echo "4. Testing imports..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from src.green_agent import GreenAgent
    print('✅ Green agent imports OK')
except Exception as e:
    print(f'❌ Green agent import error: {e}')

try:
    from src.white_agent import WhiteAgent
    print('✅ White agent imports OK')
except Exception as e:
    print(f'❌ White agent import error: {e}')
"

# Run quick test
echo ""
echo "5. Running quick assessment (3 samples)..."
echo "   This will take ~30-60 seconds..."
echo ""

python3 src/launcher.py --white-agent gpt --samples 3

# Check results
echo ""
echo "6. Checking results..."
if [ -d "results" ]; then
    latest=$(ls -t results/a2a_assessment_*.json 2>/dev/null | head -1)
    if [ -n "$latest" ]; then
        echo "✅ Results saved to: $latest"
        echo ""
        echo "Sample output:"
        head -20 "$latest"
    else
        echo "⚠️  No assessment results found"
    fi
else
    echo "⚠️  Results directory not found"
fi

echo ""
echo "======================================================"
echo "✅ Test Complete!"
echo "======================================================"
echo ""
echo "To run manual tests:"
echo "  1. Start green agent: python3 -m src.green_agent.server"
echo "  2. Start white agent: python3 -m src.white_agent.server --agent gpt"
echo "  3. Run launcher: python3 src/launcher.py --samples 5"
echo ""

