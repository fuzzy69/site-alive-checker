# -*- coding: UTF-8 -*-
#!/usr/bin/env python

from time import sleep

import requests

from .conf import HEADERS
from .defaults import TIMEOUT

def check_alive(url, timeout=TIMEOUT):
    status_code = None
    msg = ''
    # sleep(0.1)
    try:
        print(url)
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=timeout)
        if r.status_code != 200:
            r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=timeout)
        status_code = r.status_code
    except requests.exceptions.ReadTimeout as e:
        msg = str(e)
    except Exception as e:
        msg = str(e)
    print(msg)
    return status_code, msg

def split_list(li, n):
    k, m = divmod(len(li), n)

    return (li[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))