"""
Quick start verification script
Checks if the project is ready to run
"""
import sys
import os
from pathlib import Path


def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required, current:", sys.version)
        return False
    print("✅ Python version:", sys.version.split()[0])
    return True


def check_files():
    """Check required files exist"""
    required_files = [
        "requirements.txt",
        "config.example.yaml",
        "src/main.py",
        "src/config.py",
        "templates/report.html",
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        return False
    
    print("✅ All required files present")
    return True


def check_config():
    """Check config file"""
    if not Path("config.yaml").exists():
        print("⚠️  config.yaml not found. Please copy from config.example.yaml")
        return False
    
    print("✅ config.yaml exists")
    return True


def check_api_key():
    """Check API key environment variable"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ DEEPSEEK_API_KEY environment variable not set")
        print("   Set it with:")
        print("   Windows: $env:DEEPSEEK_API_KEY=\"your-key\"")
        print("   Linux/Mac: export DEEPSEEK_API_KEY=\"your-key\"")
        return False
    
    print("✅ DEEPSEEK_API_KEY is set")
    return True


def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import requests
        import bs4
        import schedule
        import yaml
        print("✅ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}")
        print("   Install with: pip install -r requirements.txt")
        return False


def check_directories():
    """Check/create required directories"""
    dirs = ["data", "logs", "reports"]
    
    for dir_name in dirs:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    print("✅ Required directories created")
    return True


def main():
    """Run all checks"""
    print("=" * 50)
    print("🦋 Cocoon Breaker - Startup Verification")
    print("=" * 50)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Files", check_files),
        ("Configuration", check_config),
        ("API Key", check_api_key),
        ("Dependencies", check_dependencies),
        ("Directories", check_directories),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            results.append(check_func())
        except Exception as e:
            print(f"❌ {name} check failed: {e}")
            results.append(False)
        print()
    
    print("=" * 50)
    if all(results):
        print("✅ All checks passed! Ready to start.")
        print()
        print("Start the server with:")
        print("  python src/main.py")
        print()
        print("Then visit:")
        print("  http://localhost:8000/static/index.html")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
