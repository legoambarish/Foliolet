import sys
import urllib.request
import urllib.error

def healthy(service):
    if service == 'evm':
        request = urllib.request.Request('http://127.0.0.1:8548',
            data=b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}',
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request, timeout=3) as response:
            return b'0x539' in response.read(1000)
    if service == 'backend':
        try:
            urllib.request.urlopen('http://127.0.0.1:8088/api/wallet', timeout=3)
        except urllib.error.HTTPError as error:
            return error.code == 401
        return False
    with urllib.request.urlopen('http://127.0.0.1:8000/login/', timeout=3) as response:
        return response.status == 200 and b'csrfmiddlewaretoken' in response.read(20000)

if __name__ == '__main__':
    try: sys.exit(0 if healthy(sys.argv[1]) else 1)
    except Exception: sys.exit(1)
