#!/bin/bash

echo "🚀 HDI Setup Script"
echo "=================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1)
echo "Found: $python_version"

# Create virtual environment
echo -e "\nCreating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo -e "\nUpgrading pip..."
pip install --upgrade pip

# Install requirements
echo -e "\nInstalling requirements..."
pip install -r requirements.txt

# Check if Redis is installed (for caching)
echo -e "\nChecking for Redis..."
if command -v redis-cli &> /dev/null; then
    echo "✓ Redis is installed"
    redis_version=$(redis-cli --version)
    echo "  Version: $redis_version"
else
    echo "⚠️  Redis not found. Install Redis for caching support:"
    echo "  macOS: brew install redis"
    echo "  Ubuntu: sudo apt-get install redis-server"
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo -e "\nCreating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your Perplexity API key"
fi

echo -e "\n✅ Setup complete!"
echo -e "\nNext steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start Redis (if installed): redis-server"
echo "3. Run the API: python run.py"
echo "4. Test Perplexity: python test_perplexity.py"
echo "5. Test HCAD: python test_hcad.py"
echo -e "\nAPI will be available at: http://localhost:5000"
echo "Swagger docs at: http://localhost:5000/docs"