import sys
import os
import requests

def test_stt(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    url = "http://127.0.0.1:8000/api/stt"
    
    print(f"Testing STT Endpoint: {url}")
    print(f"Audio file: {file_path}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    print("-" * 40)
    
    try:
        with open(file_path, 'rb') as f:
            files = {'audio': (os.path.basename(file_path), f, 'audio/webm')}
            response = requests.post(url, files=files)
            
        print(f"Status Code: {response.status_code}")
        try:
            print("Response JSON:")
            print(response.json())
        except:
            print("Response Text:")
            print(response.text)
            
    except Exception as e:
        print(f"Error connecting to backend: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_stt.py <path_to_webm_file>")
        sys.exit(1)
        
    test_stt(sys.argv[1])
