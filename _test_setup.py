#!/usr/bin/env python3
"""
Test script to verify the setup for the Audio to Notion processor.

This script checks:
1. Environment variables
2. OpenAI API connectivity
3. Notion API connectivity
4. Zotero API connectivity
5. File system permissions
"""

import os
import requests
from dotenv import load_dotenv

def test_environment_variables():
    """Test if all required environment variables are set."""
    print("1. Testing environment variables...")
    
    load_dotenv()
    
    required_vars = [
        "OPENAI_API_KEY",
        "NOTION_TOKEN", 
        "NOTION_DATABASE_ID"
    ]
    
    optional_vars = [
        "ZOTERO_API_KEY",
        "ZOTERO_USER_ID",
        "ZOTERO_LIBRARY_TYPE"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"  ✓ {var}: {'*' * (len(value) - 8) + value[-8:] if len(value) > 8 else '*' * len(value)}")
    
    # Check optional Zotero variables
    zotero_vars_present = 0
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            zotero_vars_present += 1
            print(f"  ✓ {var}: {'*' * (len(value) - 8) + value[-8:] if len(value) > 8 else '*' * len(value)}")
        else:
            print(f"  - {var}: Not set (optional)")
    
    if missing_vars:
        print(f"  ✗ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("  ✓ All required environment variables are set")
    if zotero_vars_present == len(optional_vars):
        print("  ✓ All Zotero variables are set")
    elif zotero_vars_present > 0:
        print(f"  ⚠ Partial Zotero setup ({zotero_vars_present}/{len(optional_vars)} variables)")
    else:
        print("  - Zotero integration not configured")
    
    return True

def test_openai_api():
    """Test OpenAI API connectivity."""
    print("\n2. Testing OpenAI API...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test with a simple request
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, this is a test."}
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            print("  ✓ OpenAI API is accessible")
            return True
        else:
            print(f"  ✗ OpenAI API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"  ✗ OpenAI API connection failed: {str(e)}")
        return False

def test_notion_api():
    """Test Notion API connectivity."""
    print("\n3. Testing Notion API...")
    
    token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not token or not database_id:
        print("  - Notion API test skipped (missing credentials)")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    
    try:
        # Test database access
        response = requests.get(
            f"https://api.notion.com/v1/databases/{database_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print("  ✓ Notion API is accessible")
            print(f"  ✓ Database found: {response.json().get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
            return True
        else:
            print(f"  ✗ Notion API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"  ✗ Notion API connection failed: {str(e)}")
        return False

def test_zotero_api():
    """Test Zotero API connectivity."""
    print("\n4. Testing Zotero API...")
    
    api_key = os.getenv("ZOTERO_API_KEY")
    user_id = os.getenv("ZOTERO_USER_ID")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
    
    if not api_key or not user_id:
        print("  - Zotero API test skipped (missing credentials)")
        return False
    
    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3"
    }
    
    try:
        # Test user library access
        response = requests.get(
            f"https://api.zotero.org/{library_type}s/{user_id}/collections",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            collections = response.json()
            print("  ✓ Zotero API is accessible")
            print(f"  ✓ Found {len(collections)} collections in library")
            return True
        else:
            print(f"  ✗ Zotero API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"  ✗ Zotero API connection failed: {str(e)}")
        return False

def test_file_system():
    """Test file system permissions."""
    print("\n5. Testing file system permissions...")
    
    test_folder = "./test_audio_files"
    test_state_file = "./test_state.json"
    
    try:
        # Test folder creation
        os.makedirs(test_folder, exist_ok=True)
        print("  ✓ Can create folders")
        
        # Test file writing
        with open(test_state_file, 'w') as f:
            f.write('{"test": "data"}')
        print("  ✓ Can write files")
        
        # Test file reading
        with open(test_state_file, 'r') as f:
            data = f.read()
        print("  ✓ Can read files")
        
        # Cleanup
        os.remove(test_state_file)
        os.rmdir(test_folder)
        print("  ✓ Can delete files and folders")
        
        return True
        
    except Exception as e:
        print(f"  ✗ File system test failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("=== Audio to Notion Processor Setup Test ===\n")
    
    tests = [
        test_environment_variables,
        test_openai_api,
        test_notion_api,
        test_zotero_api,
        test_file_system
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed >= 3:  # At least OpenAI, file system, and one API should work
        print("✓ Core functionality is ready! Your setup is ready to use.")
        print("\nNext steps:")
        print("1. Create an 'audio_files' folder (or set AUDIO_FOLDER_PATH)")
        print("2. Add some MP3 files to the folder")
        print("3. Run: python audio_to_notion.py")
        
        if passed < total:
            print("\nOptional integrations:")
            if "Notion" not in [test.__name__ for test in tests if test()]:
                print("- Set up Notion integration for audio storage")
            if "Zotero" not in [test.__name__ for test in tests if test()]:
                print("- Set up Zotero integration for literature management")
        
        return 0
    else:
        print("✗ Core functionality is not ready. Please fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main()) 