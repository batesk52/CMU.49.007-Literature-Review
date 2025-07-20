#!/usr/bin/env python3
"""
Test script to debug Zotero authentication issues
"""

import os
from dotenv import load_dotenv
from pyzotero import zotero

def test_zotero_auth():
    """Test Zotero authentication and help debug issues"""
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    user_id = os.getenv("ZOTERO_USER_ID")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
    api_key = os.getenv("ZOTERO_API_KEY")
    
    print("=== Zotero Authentication Debug ===")
    print(f"User ID: {user_id}")
    print(f"Library Type: {library_type}")
    print(f"API Key: {'✓ Set' if api_key else '✗ MISSING'}")
    
    if not api_key:
        print("\n❌ ERROR: ZOTERO_API_KEY is missing from your .env file!")
        print("\nTo fix this:")
        print("1. Go to https://www.zotero.org/settings/keys")
        print("2. Click 'Create a new key'")
        print("3. Give it a name (e.g., 'Anki Integration')")
        print("4. Set permissions to 'Read' for your library")
        print("5. Copy the generated key")
        print("6. Add this line to your .env file:")
        print("   ZOTERO_API_KEY=your_api_key_here")
        return False
    
    if not user_id:
        print("\n❌ ERROR: ZOTERO_USER_ID is missing from your .env file!")
        print("Add your Zotero user ID to the .env file")
        return False
    
    # Try to connect
    try:
        print(f"\n🔗 Testing connection to Zotero...")
        zot = zotero.Zotero(user_id, library_type, api_key)
        
        # Test with a simple API call
        collections = zot.collections(limit=1)
        print("✅ Successfully connected to Zotero!")
        print(f"Found {len(collections)} collection(s) in first page")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("1. API key is invalid or expired")
        print("2. User ID is incorrect")
        print("3. API key doesn't have proper permissions")
        print("4. Network connectivity issues")
        return False

if __name__ == "__main__":
    test_zotero_auth() 