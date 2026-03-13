import urllib.request
import json

def test_api():
    try:
        # Test health endpoint
        with urllib.request.urlopen('http://localhost:5000/api/health') as response:
            data = json.loads(response.read().decode())
            print('✅ API Health:', data)

        # Test imported content stats
        with urllib.request.urlopen('http://localhost:5000/api/imported/stats') as response:
            data = json.loads(response.read().decode())
            print('✅ Imported Stats:', data)

        # Test imported content list
        with urllib.request.urlopen('http://localhost:5000/api/imported') as response:
            data = json.loads(response.read().decode())
            print('✅ Imported Content:', len(data.get('content', [])), 'items')

    except Exception as e:
        print('❌ Error:', e)

if __name__ == '__main__':
    test_api()