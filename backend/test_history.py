import http.client

def test_endpoint(path):
    try:
        conn = http.client.HTTPConnection('localhost', 8000)
        conn.request('GET', path)
        response = conn.getresponse()
        print(f"{path}: {response.status}")
        body = response.read(2000)
        print(f"Response: {body.decode()[:1000]}")
        conn.close()
    except Exception as e:
        print(f"{path} error: {e}")

test_endpoint('/api/v1/history/passenger-flow')
print("\n" + "="*50 + "\n")
test_endpoint('/api/v1/history/passenger-flow/prediction')
print("\n" + "="*50 + "\n")
test_endpoint('/api/v1/history/eta/101/1')
print("\n" + "="*50 + "\n")
test_endpoint('/api/v1/history/load/1')