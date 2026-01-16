import urllib3

http = urllib3.PoolManager()
r = http.request('GET', 'http://example.com/')
print('status = {0}'.format(r.status))
print(r.data)
if r.status != 200 or not r.data:
    raise SystemExit(1)
