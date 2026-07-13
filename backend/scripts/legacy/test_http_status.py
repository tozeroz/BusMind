import http.client

def test_endpoint(path, description):
    try:
        conn = http.client.HTTPConnection('localhost', 8001)
        conn.request('GET', path)
        response = conn.getresponse()
        body = response.read(2000).decode()
        print(f"\n--- {description} ---")
        print(f"Endpoint: {path}")
        print(f"HTTP Status: {response.status}")
        print(f"Response: {body}")
        conn.close()
        return response.status
    except Exception as e:
        print(f"{description} error: {e}")
        return None

print("="*60)
print("Testing History Module HTTP Status Fix")
print("="*60)

# Test cases
test_endpoint('/api/v1/history/eta/101/1', 'ETA prediction not found (should return HTTP 404)')
test_endpoint('/api/v1/history/load/99999', 'Load prediction not found (should return HTTP 404)')
test_endpoint('/api/v1/history/load/1', 'Load prediction empty (should return HTTP 200)')
test_endpoint('/api/v1/history/passenger-flow', 'Passenger flow (should return HTTP 200)')

print("\n" + "="*60)
