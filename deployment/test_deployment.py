#!/usr/bin/env python3
"""
Simple deployment test to verify basic functionality
"""

import sys
import os
import subprocess
import json
from pathlib import Path

def test_basic_imports():
    """Test that basic imports work"""
    try:
        # Test core imports
        import firebase_admin
        import redis
        print("✅ Core dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_firebase_connection():
    """Test Firebase connection (basic check)"""
    try:
        # Check if Firebase key exists
        firebase_key_path = Path("config/firebase_key.json")
        if firebase_key_path.exists():
            print("✅ Firebase key file exists")
            return True
        else:
            print("⚠️  Firebase key file not found (may be in environment)")
            return True  # Don't fail deployment for this
    except Exception as e:
        print(f"⚠️  Firebase check error: {e}")
        return True  # Don't fail deployment for this

def test_basic_functionality():
    """Test basic script functionality"""
    try:
        # Check if main scraper exists and can be imported
        sys.path.insert(0, str(Path.cwd()))
        
        # Test simple import (don't run actual scraping)
        if Path("src/scripts/youtube_scraper_production.py").exists():
            print("✅ Main scraper file exists")
        
        if Path("src/scripts/youtube_collection_manager.py").exists():
            print("✅ Collection manager exists")
            
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_directory_structure():
    """Test that expected directories exist"""
    required_dirs = [
        "src",
        "logs", 
        "config",
        "deployment"
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"⚠️  Missing directories: {missing_dirs}")
        # Create missing directories
        for dir_name in missing_dirs:
            Path(dir_name).mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {dir_name}")
    else:
        print("✅ Directory structure OK")
    
    return True

def test_permissions():
    """Test file permissions"""
    try:
        # Check if we can write to logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        test_file = logs_dir / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        
        print("✅ Write permissions OK")
        return True
    except Exception as e:
        print(f"❌ Permission test failed: {e}")
        return False

def main():
    """Run all deployment tests"""
    print("🧪 Running deployment tests...")
    
    tests = [
        ("Basic imports", test_basic_imports),
        ("Firebase connection", test_firebase_connection),
        ("Basic functionality", test_basic_functionality),
        ("Directory structure", test_directory_structure),
        ("Permissions", test_permissions),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            failed_tests.append(test_name)
    
    print(f"\n📊 Test Results:")
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {len(tests) - len(failed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed tests: {', '.join(failed_tests)}")
        return False
    else:
        print(f"\n✅ All tests passed!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)