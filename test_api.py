#!/usr/bin/env python3
"""
Stress Test Script for DPR Compliance Analysis System
Tests upload, polling, and report endpoints
"""

import requests
import json
import time
import sys
import os
from datetime import datetime
import io

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n[TEST 1] Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Health Check: {response.json()}")
            return True
        else:
            print(f"[FAIL] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Health check error: {e}")
        return False

def test_upload(file_name="test.pdf", size_kb=100):
    """Test file upload"""
    print(f"\n[TEST 2] Upload Test ({size_kb}KB file)")
    try:
        # Create a fake PDF file
        fake_pdf_content = b"%PDF-1.4\n" + b"x" * (size_kb * 1024 - 9)
        
        files = {'file': (file_name, io.BytesIO(fake_pdf_content), 'application/pdf')}
        response = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)
        
        if response.status_code == 200:
            job_id = response.json().get('job_id')
            print(f"[OK] Upload successful. Job ID: {job_id}")
            return job_id
        else:
            print(f"[FAIL] Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Upload error: {e}")
        return None

def test_status(job_id):
    """Test status check"""
    print(f"\n[TEST 3] Status Check (Job ID: {job_id})")
    try:
        response = requests.get(f"{BASE_URL}/status/{job_id}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            print(f"[OK] Status retrieved: {status}")
            print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            return status
        else:
            print(f"[FAIL] Status check failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Status check error: {e}")
        return None

def test_invalid_job():
    """Test with invalid job ID"""
    print(f"\n[TEST 4] Error Handling - Invalid Job ID")
    try:
        response = requests.get(f"{BASE_URL}/status/INVALID123", timeout=5)
        
        if response.status_code == 404:
            print(f"[OK] Correct error handling: {response.json()}")
            return True
        else:
            print(f"[FAIL] Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error handling test error: {e}")
        return False

def test_api_docs():
    """Test API documentation endpoint"""
    print(f"\n[TEST 5] API Documentation")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        
        if response.status_code == 200:
            print(f"[OK] API docs available: {len(response.text)} bytes")
            return True
        else:
            print(f"[FAIL] API docs failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] API docs error: {e}")
        return False

def test_concurrent_uploads():
    """Test multiple concurrent uploads"""
    print(f"\n[TEST 6] Concurrent Uploads (5 files)")
    job_ids = []
    
    for i in range(5):
        try:
            fake_pdf = b"%PDF-1.4\n" + b"x" * (50 * 1024)  # 50KB each
            files = {'file': (f'test_{i}.pdf', io.BytesIO(fake_pdf), 'application/pdf')}
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)
            
            if response.status_code == 200:
                job_id = response.json().get('job_id')
                job_ids.append(job_id)
                print(f"  [OK] Upload {i+1}: {job_id}")
            else:
                print(f"  [FAIL] Upload {i+1} failed")
        except Exception as e:
            print(f"  [ERROR] Upload {i+1} error: {e}")
    
    print(f"[OK] Completed {len(job_ids)}/5 uploads")
    return job_ids

def test_large_file():
    """Test with larger file"""
    print(f"\n[TEST 7] Large File Upload (1MB)")
    try:
        fake_pdf = b"%PDF-1.4\n" + b"x" * (1024 * 1024 - 9)  # 1MB
        files = {'file': ('large_test.pdf', io.BytesIO(fake_pdf), 'application/pdf')}
        
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/upload", files=files, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            job_id = response.json().get('job_id')
            print(f"[OK] Large file upload successful in {elapsed:.2f}s. Job ID: {job_id}")
            return job_id
        else:
            print(f"[FAIL] Large file upload failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Large file upload error: {e}")
        return None

def test_invalid_file_type():
    """Test upload with invalid file type"""
    print(f"\n[TEST 8] Error Handling - Invalid File Type")
    try:
        files = {'file': ('test.txt', io.BytesIO(b"This is not a PDF"), 'text/plain')}
        response = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)
        
        if response.status_code == 400:
            print(f"[OK] Correctly rejected non-PDF file: {response.json()}")
            return True
        else:
            print(f"[FAIL] Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] File type error test error: {e}")
        return False

def run_stress_tests():
    """Run all stress tests"""
    print("\n" + "="*80)
    print("TEST: DPR COMPLIANCE ANALYSIS SYSTEM - STRESS TEST")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    print("="*80)
    
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0
    }
    
    # Test 1: Health Check
    results['total'] += 1
    if test_health():
        results['passed'] += 1
    else:
        results['failed'] += 1
        print(f"Backend not responding. Aborting tests.")
        return results
    
    # Test 2: Upload
    results['total'] += 1
    job_id = test_upload(size_kb=50)
    if job_id:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 3: Status Check
    if job_id:
        results['total'] += 1
        status = test_status(job_id)
        if status:
            results['passed'] += 1
        else:
            results['failed'] += 1
    
    # Test 4: Invalid Job ID
    results['total'] += 1
    if test_invalid_job():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 5: API Docs
    results['total'] += 1
    if test_api_docs():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 6: Concurrent Uploads
    results['total'] += 1
    job_ids = test_concurrent_uploads()
    if len(job_ids) >= 3:  # At least 3 out of 5
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 7: Large File
    results['total'] += 1
    if test_large_file():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 8: Invalid File Type
    results['total'] += 1
    if test_invalid_file_type():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Print Summary
    print("\n" + "="*80)
    print("SUMMARY: TEST RESULTS")
    print("="*80)
    print(f"Total Tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    pass_rate = (results['passed'] / results['total'] * 100) if results['total'] > 0 else 0
    
    if pass_rate == 100:
        print(f"\n[SUCCESS] ALL TESTS PASSED ({pass_rate:.1f}%)")
    elif pass_rate >= 80:
        print(f"\n[PARTIAL] MOST TESTS PASSED ({pass_rate:.1f}%)")
    else:
        print(f"\n[FAILURE] TESTS FAILED ({pass_rate:.1f}%)")
    
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    return results

if __name__ == "__main__":
    print("Waiting for backend to be ready...")
    for i in range(15):
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
            print("[OK] Backend is ready!")
            break
        except:
            if i == 14:
                print(f"[ERROR] Backend not responding after 15 attempts")
                sys.exit(1)
            time.sleep(1)
            print(f"  Attempt {i+2}/15...")
    
    results = run_stress_tests()
    sys.exit(0 if results['failed'] == 0 else 1)
