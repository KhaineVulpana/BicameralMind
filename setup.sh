#!/bin/bash
# Bicameral Mind Setup Script

echo " Bicameral Mind Setup"
echo "======================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "OK Python version: $python_version"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo " Ollama not found. Install from: https://ollama.ai"
    exit 1
fi
echo "OK Ollama installed"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create data directories
echo ""
echo "Creating data directories..."
mkdir -p data/knowledge_base data/vector_store data/memory logs

# Pull recommended model
echo ""
echo "Pulling recommended model (qwen3:14b)..."
echo "This may take a while..."
ollama pull qwen3:14b

# Alternative models
echo ""
echo "Other recommended models:"
echo "  - ollama pull llama3.1:8b    (smaller, faster)"
echo "  - ollama pull mistral         (alternative)"

echo ""
echo " Setup complete!"
echo ""
echo "Run: python main.py"
