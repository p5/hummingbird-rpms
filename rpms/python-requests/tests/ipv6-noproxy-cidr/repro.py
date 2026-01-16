import subprocess
import requests
import os
import time
import atexit

subprocesses = []

python = os.environ.get("PYTHON","python3")
server_url = os.environ.get("SERVER_URL", None)
testing_no_proxy = os.environ.get("TESTING_NO_PROXY", None)

# Clean up
@atexit.register
def cleanup():
    print("Cleaning up subprocesses")
    for process in subprocesses:
        process.terminate()

    time.sleep(1)

    for process in subprocesses:
        process.wait()

# Part one, assert that everything works
if server_url is None:
    print("starting server")
    p = subprocess.Popen([python, "server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocesses.append(p)
    time.sleep(1)
    server_url = "http://[::1]:8888"
    no_proxy = "::1/128"
else:
    print(f"using provided {server_url} as server")
    print(f"using provided {testing_no_proxy} as NO_PROXY value")
    assert testing_no_proxy, "TESTING_NO_PROXY envar missing"

# Send request and check the response

print("sending first request")
assert requests.get(server_url, timeout=2).text.startswith("Hello")


# Part two, dummy proxy causes timeout, that's fine

# Start proxy
print("starting proxy")
p = subprocess.Popen(["nc", "-k", "-l", "10000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
subprocesses.append(p)
time.sleep(1)

# Set proxy to environment
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10000"

# Send request, expect timeout because proxy is dummy and do not respond
print("Sending request via proxy")
try:
    requests.get(server_url, timeout=2)
except requests.exceptions.ReadTimeout:
    print("timeout is fine, expected")
    pass

# Part three, NO_PROXY bypass the proxy and the request should work as before

os.environ["NO_PROXY"] = testing_no_proxy or no_proxy

print("sending last request")
try:
    assert requests.get(server_url, timeout=2).text.startswith("Hello")
except requests.exceptions.ReadTimeout:
    print("PROBLEM - the last request timed out, NO_PROXY setting does not work!")
    raise SystemExit(1)
else:
    print("OK - NO_PROXY setting works fine - the last request bypassed proxy")
