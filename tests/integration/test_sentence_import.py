#!/usr/bin/env python3
"""Test script to verify sentence import flow through API and database."""

import sys
import os
import json
import requests
import time
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_directly():
    """Test database add_imported_content function directly."""
    print("\n" + "="*60)
    print("TEST 1: Database Direct Test")
    print("="*60)
    
    try:
        from src.core.database import FlashcardDatabase
        
        db = FlashcardDatabase('test_sentence_direct.db')
        
        # Add a test sentence
        print("\n[DB] Adding test sentence...")
        content_id = db.add_imported_content(
            content_type='sentence',
            content='This is a test sentence for verification.',
            url='http://test.example.com',
            title='Test Page',
            language='en'
        )
        print(f"[DB] ✓ Added sentence with ID: {content_id}")
        
        # Retrieve it
        print("\n[DB] Retrieving all imported content...")
        content = db.get_imported_content(limit=100)
        print(f"[DB] ✓ Retrieved {len(content)} items")
        
        # Find our test item
        found = False
        for item in content:
            if item['content_type'] == 'sentence' and 'test sentence' in item['content']:
                found = True
                print(f"[DB] ✓ Found test sentence:")
                print(f"    ID: {item['id']}")
                print(f"    Type: {item['content_type']}")
                print(f"    Content: {item['content']}")
                print(f"    URL: {item['url']}")
                print(f"    Created: {item['created_at']}")
                break
        
        if found:
            print("\n✓ DATABASE TEST PASSED")
            return True
        else:
            print("\n✗ DATABASE TEST FAILED: Item not found after retrieval")
            return False
            
    except Exception as e:
        print(f"\n✗ DATABASE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Test API endpoint for adding sentences."""
    print("\n" + "="*60)
    print("TEST 2: API Endpoint Test")
    print("="*60)
    
    try:
        # Check if API is running
        print("\n[API] Checking API health...")
        try:
            health = requests.get('http://localhost:5000/api/health', timeout=3)
            print(f"[API] ✓ Health check: {health.status_code}")
        except:
            print("[API] ✗ API not responding. Attempting to start server...")
            # Try to start server
            time.sleep(2)
        
        # Send POST request to add sentence
        print("\n[API] Sending POST /api/imported to add sentence...")
        payload = {
            'content_type': 'sentence',
            'content': 'Testing the API endpoint for sentence import.',
            'url': 'http://api-test.example.com',
            'title': 'API Test Page',
            'language': 'en'
        }
        
        response = requests.post(
            'http://localhost:5000/api/imported',
            json=payload,
            timeout=5
        )
        
        print(f"[API] Response status: {response.status_code}")
        data = response.json()
        print(f"[API] Response: {json.dumps(data, indent=2)}")
        
        if data.get('success'):
            content_id = data.get('content_id')
            print(f"[API] ✓ Successfully added sentence with ID: {content_id}")
            
            # Now verify by retrieving
            print("\n[API] Retrieving imported content...")
            get_response = requests.get('http://localhost:5000/api/imported?limit=10')
            get_data = get_response.json()
            
            if get_data.get('success'):
                content = get_data.get('content', [])
                print(f"[API] ✓ Retrieved {len(content)} items")
                
                # Find our test item
                for item in content:
                    if item.get('id') == content_id:
                        print(f"[API] ✓ Found imported sentence:")
                        print(f"    ID: {item['id']}")
                        print(f"    Type: {item['content_type']}")
                        print(f"    Content: {item['content']}")
                        print(f"    URL: {item['url']}")
                        print("\n✓ API TEST PASSED")
                        return True
                
                print("\n✗ API TEST FAILED: Added item not found in retrieval")
                return False
            else:
                print(f"\n✗ API TEST FAILED: Could not retrieve content")
                return False
        else:
            print(f"\n✗ API TEST FAILED: {data.get('error', 'Unknown error')}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ API TEST FAILED: Cannot connect to API on localhost:5000")
        print("   Make sure to start the server first with: .\\manage-server.ps1 server-bg")
        return False
    except Exception as e:
        print(f"\n✗ API TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_browser_extension_simulation():
    """Simulate browser extension sending data."""
    print("\n" + "="*60)
    print("TEST 3: Browser Extension Simulation")
    print("="*60)
    
    try:
        print("\n[BROWSER] Simulating browser extension context menu import...")
        
        # Simulate what background.js sends
        payload = {
            'content_type': 'sentence',
            'content': 'Le français est une belle langue.',
            'url': 'https://learn.example.com/french',
            'title': 'French Learning Page'
        }
        
        print(f"[BROWSER] Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            'http://localhost:5000/api/imported',
            json=payload,
            timeout=5
        )
        
        print(f"[BROWSER] Response: {response.status_code}")
        data = response.json()
        
        if data.get('success'):
            print(f"[BROWSER] ✓ Successfully sent sentence to API")
            print(f"[BROWSER] Content ID: {data['content_id']}")
            print("\n✓ BROWSER SIMULATION TEST PASSED")
            return True
        else:
            print(f"[BROWSER] ✗ API error: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n✗ BROWSER SIMULATION TEST FAILED: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("SENTENCE IMPORT VERIFICATION TEST SUITE")
    print("="*60)
    
    # Test 1: Database
    db_pass = test_database_directly()
    
    # Test 2 & 3: API (requires running server)
    api_pass = test_api_endpoint()
    browser_pass = test_browser_extension_simulation()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Database Direct: {'✓ PASS' if db_pass else '✗ FAIL'}")
    print(f"API Endpoint:    {'✓ PASS' if api_pass else '✗ FAIL'}")
    print(f"Browser Sim:     {'✓ PASS' if browser_pass else '✗ FAIL'}")
    
    if db_pass and api_pass and browser_pass:
        print("\n✓ ALL TESTS PASSED - System is working correctly!")
    else:
        print("\n✗ SOME TESTS FAILED - See details above")
    
    print("="*60)

if __name__ == '__main__':
    main()
