#!/usr/bin/env python3
"""
Quick test script to verify the API backend is ready for the extension
Tests both the health check and import endpoints
"""

import requests
import json
from datetime import datetime

API_URL = 'http://localhost:5000/api'

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def test_health_check():
    """Test the /api/health endpoint"""
    print_header("TEST 1: Health Check")
    
    try:
        response = requests.get(f'{API_URL}/health')
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('status') == 'ok':
            print("\n✅ PASS: API is running and responding correctly")
            return True
        else:
            print("\n❌ FAIL: Unexpected response")
            return False
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

def test_import_word():
    """Test importing a word"""
    print_header("TEST 2: Import Word")
    
    payload = {
        "content_type": "word",
        "content": "test",
        "url": "https://example.com",
        "title": "Example Page"
    }
    
    try:
        response = requests.post(f'{API_URL}/imported', json=payload)
        data = response.json()
        
        print(f"Sent: {json.dumps(payload, indent=2)}")
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            print(f"\n✅ PASS: Word imported successfully (ID: {data.get('content_id')})")
            return True, data.get('content_id')
        else:
            print("\n❌ FAIL: Import failed")
            return False, None
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False, None

def test_import_sentence():
    """Test importing a sentence"""
    print_header("TEST 3: Import Sentence")
    
    payload = {
        "content_type": "sentence",
        "content": "The quick brown fox jumps over the lazy dog.",
        "url": "https://example.com/article",
        "title": "Article Title"
    }
    
    try:
        response = requests.post(f'{API_URL}/imported', json=payload)
        data = response.json()
        
        print(f"Sent: {json.dumps(payload, indent=2)}")
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            print(f"\n✅ PASS: Sentence imported successfully (ID: {data.get('content_id')})")
            return True, data.get('content_id')
        else:
            print("\n❌ FAIL: Import failed")
            return False, None
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False, None

def test_get_imported_content():
    """Test retrieving imported content"""
    print_header("TEST 4: Retrieve Imported Content")
    
    try:
        response = requests.get(f'{API_URL}/imported?limit=10')
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response (first 2 items):")
        
        if data.get('success') and data.get('content'):
            for item in data.get('content', [])[:2]:
                print(f"\n  ID: {item.get('id')}")
                print(f"  Type: {item.get('content_type')}")
                print(f"  Content: {item.get('content')[:50]}...")
                print(f"  URL: {item.get('url')}")
                print(f"  Title: {item.get('title')}")
        
        if response.status_code == 200 and data.get('success'):
            print(f"\n✅ PASS: Retrieved {len(data.get('content', []))} items")
            return True
        else:
            print("\n❌ FAIL: Could not retrieve content")
            return False
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

def test_missing_fields():
    """Test error handling for missing required fields"""
    print_header("TEST 5: Missing Required Fields")
    
    # Test missing content
    payload = {
        "content_type": "word",
        "url": "https://example.com"
        # Missing "content"
    }
    
    try:
        response = requests.post(f'{API_URL}/imported', json=payload)
        data = response.json()
        
        print(f"Payload (missing 'content'): {json.dumps(payload, indent=2)}")
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code >= 400 and not data.get('success'):
            print("\n✅ PASS: API correctly rejected invalid request")
            return True
        else:
            print("\n❌ FAIL: API did not reject invalid request")
            return False
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

def test_filter_by_type():
    """Test filtering imported content by type"""
    print_header("TEST 6: Filter by Content Type")
    
    try:
        response = requests.get(f'{API_URL}/imported?type=word')
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Filtered by type='word':")
        
        if data.get('success') and data.get('content'):
            for item in data.get('content', [])[:2]:
                print(f"\n  Type: {item.get('content_type')}")
                print(f"  Content: {item.get('content')[:50]}...")
        
        if response.status_code == 200 and data.get('success'):
            print(f"\n✅ PASS: Retrieved {len(data.get('content', []))} items of type 'word'")
            return True
        else:
            print("\n❌ FAIL: Could not filter content")
            return False
    except Exception as e:
        print(f"❌ FAIL: {type(e).__name__}: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  BROWSER EXTENSION ↔ API BACKEND COMPATIBILITY TEST")
    print("="*60)
    print(f"\nTarget API: {API_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health_check()))
    word_pass, word_id = test_import_word()
    results.append(("Import Word", word_pass))
    sentence_pass, sentence_id = test_import_sentence()
    results.append(("Import Sentence", sentence_pass))
    results.append(("Retrieve Content", test_get_imported_content()))
    results.append(("Error Handling", test_missing_fields()))
    results.append(("Filter by Type", test_filter_by_type()))
    
    # Summary
    print_header("SUMMARY")
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("✅ ALL TESTS PASSED - Backend is ready for extension!\n")
        return 0
    else:
        print("❌ SOME TESTS FAILED - See details above\n")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
