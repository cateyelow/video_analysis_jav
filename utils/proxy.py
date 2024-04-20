import os
import time
import requests
from random import choice, random, shuffle

from requests.exceptions import RequestException, ConnectionError, Timeout

import concurrent.futures

from tqdm import tqdm


def download_proxies(protocol):
    url = (
        f"https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/{protocol}.txt"
    )
    directory = "proxy"
    if not os.path.exists(directory):
        os.makedirs(directory)

    output_file = os.path.join(directory, f"{protocol}.txt")

    print(f"Downloading {protocol} proxies...")
    response = requests.get(url)
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"{protocol} proxies downloaded to {output_file}\n")


def is_proxy_working(proxy, type="socks5"):
    urls_to_check = ["http://httpbin.org/ip"]
    url = choice(urls_to_check)
    try:
        # SOCKS5_PROXY = {"http": "socks5://ip:port", "https": "socks5://ip:port"}
        # HTTP_ PROXY =  {"http": "http://ip:port", "https": "https://ip:port"}

        if type == "socks5":
            PROXY = {"http": f"socks5://{proxy}", "https": f"socks5://{proxy}"}
        else:
            PROXY = {"http": f"http://{proxy}", "https": f"https://{proxy}"}

        response = requests.get(
            url=url,
            proxies=PROXY,
            timeout=0.5,
        )
        if response.status_code == 200:
            return True
    except (RequestException, ConnectionError, Timeout):
        pass
    return False


def select_random_proxy():
    proxy_type = choice(["socks5, http"])  # Choose either socks5 or http

    if proxy_type == "socks5":
        proxy_address = choice(socks5_proxies)
        full_proxy = f"socks5://{proxy_address}"
        return full_proxy
    else:
        proxy_address = choice(http_proxies)
        full_proxy = f"http://{proxy_address}"
        return full_proxy


def select_random_proxy_with_validation():
    proxy_type = choice(["http"])  # Choose either socks5 or http

    if proxy_type == "socks5":
        valid_proxy = False
        while not valid_proxy and socks5_proxies:
            proxy_address = choice(socks5_proxies)
            full_proxy = f"socks5://{proxy_address}"
            valid_proxy = is_proxy_working(proxy_address, type="socks5")
            if not valid_proxy:
                socks5_proxies.remove(proxy_address)
        if valid_proxy:
            return full_proxy
    else:
        valid_proxy = False
        while not valid_proxy and http_proxies:
            proxy_address = choice(http_proxies)
            full_proxy = f"http://{proxy_address}"
            valid_proxy = is_proxy_working(proxy_address, type="http")
            if not valid_proxy:
                http_proxies.remove(proxy_address)
        if valid_proxy:
            return full_proxy

    return None


def check_proxy(proxy, type):
    is_working = is_proxy_working(proxy, type=type)
    return proxy, is_working


def filter_working_proxies(proxies, type):
    working_proxies = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(check_proxy, proxy, type) for proxy in proxies]

        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(proxies),
            desc=f"Checking {type} proxies",
        ):
            proxy, is_working = future.result()
            if is_working:
                working_proxies.append(proxy)

    return working_proxies


# protocols = ["socks5", "socks4", "http"]

# for protocol in protocols:
#     download_proxies(protocol)


# with open("proxy/socks5.txt") as f:
#     socks5_proxies = f.read().splitlines()
#     socks5_proxies = filter_working_proxies(socks5_proxies, "socks5")

# with open("proxy/http.txt") as f:
#     http_proxies = f.read().splitlines()
#     http_proxies = filter_working_proxies(http_proxies, "http")


####################### Program Proxy #######################


def get_proxy():
    with open("iplist.txt", mode="r") as f:
        ip_list = f.read().splitlines()

    shuffle(ip_list)
    proxy = choice(ip_list)
    return proxy
