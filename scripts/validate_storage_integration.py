#!/usr/bin/env python3
"""
Quick validation script to verify Supabase Storage integration is ready.
Run this after installation to check everything is configured correctly.
"""

import sys
from pathlib import Path

def print_status(check, status, message):
    """Print colored status message."""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {check}: {message}")
    return status

def main():
    print("=" * 60)
    print("Supabase Storage Integration - Validation")
    print("=" * 60)
    print()
    
    all_checks_passed = True
    
    # Check 1: Files exist
    print("📁 Checking files...")
    files_to_check = [
        "app/services/supabase_storage_service.py",
        "app/services/storage_manager.py",
        "app/services/storage_integration_helper.py",
        "scripts/migrate_to_supabase.py",
        "docs/STORAGE_SETUP.md",
        "docs/STORAGE_TESTING.md",
        ".env.example"
    ]
    
    for file in files_to_check:
        exists = Path(file).exists()
        all_checks_passed &= print_status(
            file, 
            exists,
            "Found" if exists else "Missing"
        )
    
    print()
    
    # Check 2: Dependencies
    print("📦 Checking dependencies...")
    required_packages = [
        ("supabase", "Supabase Python client"),
        ("loguru", "Logging library"),
    ]
    
    for package, description in required_packages:
        try:
            __import__(package)
            print_status(package, True, f"{description} installed")
        except ImportError:
            all_checks_passed &= print_status(
                package, 
                False, 
                f"{description} not installed - run: pip install {package}"
            )
    
    print()
    
    # Check 3: Syntax validation
    print("🔍 Checking syntax...")
    import py_compile
    
    for file in files_to_check[:3]:  # Only check Python files
        if not file.endswith('.py'):
            continue
        try:
            py_compile.compile(file, doraise=True)
            print_status(file, True, "Syntax valid")
        except Exception as e:
            all_checks_passed &= print_status(file, False, f"Syntax error: {e}")
    
    print()
    
    # Check 4: Configuration hints
    print("⚙️  Configuration status...")
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_example.exists():
        print_status(".env.example", True, "Template available")
    
    if env_file.exists():
        print_status(".env", True, "Found - check Supabase variables")
        print("   💡 Tip: Verify SUPABASE_URL and SUPABASE_SERVICE_KEY are set")
    else:
        print_status(".env", False, "Not found - copy from .env.example")
        print("   📝 Run: cp .env.example .env")
    
    print()
    
    # Summary
    print("=" * 60)
    if all_checks_passed:
        print("✅ All checks passed!")
        print()
        print("Next steps:")
        print("1. Configure Supabase credentials in .env")
        print("2. Read docs/STORAGE_SETUP.md for setup guide")
        print("3. Run docs/STORAGE_TESTING.md tests")
        print("4. (Optional) Migrate existing projects:")
        print("   python scripts/migrate_to_supabase.py --dry-run")
    else:
        print("❌ Some checks failed")
        print()
        print("Please fix the issues above and run this script again.")
        sys.exit(1)
    
    print("=" * 60)

if __name__ == "__main__":
    main()
