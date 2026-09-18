import os
os.environ["BACKEND_API_KEY"] = "smoke-test-key"
os.environ["TURSO_DATABASE_URL"] = "file:/tmp/exo-agent-smoke.sqlite3"
os.environ["TURSO_AUTH_TOKEN"] = "smoke-test-token"
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
assert client.get('/health').json() == {'status': 'ok'}
headers = {'X-API-Key': 'smoke-test-key'}
created = client.post('/jobs', headers=headers, json={'repository':'org/repo','ref':'main','findings':[{'origin':'ci','path':'src/a.py','test_name':'test_a','failure_type':'AssertionError'}]})
assert created.status_code == 200
assert client.get('/jobs', headers=headers).status_code == 200
assert client.get('/findings', headers=headers).status_code == 200
assert client.get('/scope', headers=headers).status_code == 200
print('API smoke OK')
