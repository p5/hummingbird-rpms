import requests
from requests import *

class ExceptionRequests(Exception):
    pass

if __name__=="__main__":
    r=requests.get('https://redhat.com')
    if r.status_code!=200 or \
       not r.text or r.encoding.lower() != 'utf-8':
        raise ExceptionRequests("Sanity error")
