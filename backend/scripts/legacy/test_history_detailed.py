import http.client

def test_endpoint(path):
    try:
        conn = http.client.HTTPConnection('localhost', 8001)
        conn.request('GET', path)
        response = conn.getresponse()
        print(f"{path}: {response.status}")
        body = response.read(4000)
        print(f"Response: {body.decode()}")
        conn.close()
        return response.status == 200
    except Exception as e:
        print(f"{path} error: {e}")
        return False

print("="*60)
print("Testing History Module APIs")
print("="*60)

endpoints = [
    '/api/v1/history/passenger-flow',
    '/api/v1/history/passenger-flow/prediction',
    '/api/v1/history/eta/101/1',
    '/api/v1/history/load/1',
    '/api/v1/history/eta/line/1',
    '/api/v1/history/load/line/1'
]

success_count = 0
for endpoint in endpoints:
    print(f"\n--- Testing: {endpoint} ---")
    if test_endpoint(endpoint):
        success_count += 1

print("\n" + "="*60)
print(f"Summary: {success_count}/{len(endpoints)} endpoints passed")
print("="*60)
