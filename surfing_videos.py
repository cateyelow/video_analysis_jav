from bs4 import BeautifulSoup
import requests
import yt_dlp
from utils.crawler import Crawling
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import os
import asyncio
from torrentp import TorrentDownloader

proxies = {
    "http": "socks5://127.0.0.1:9050",
    "https": "socks5://127.0.0.1:9050",
}


def load_progressed_magnets():
    if os.path.exists("progressed.txt"):
        with open("progressed.txt", "r") as f:
            return set(line.strip() for line in f)
    return set()


def save_progressed_magnet(magnet):
    with open("progressed.txt", "a") as f:
        f.write(f"{magnet}\n")


async def download_torrent(magnet):
    torrentfile = TorrentDownloader(file_path=magnet, save_path="videos")
    await torrentfile.start_download()
    print("Downloaded:", magnet)


async def main():
    progressed_magnets = load_progressed_magnets()

    for page in range(1, 51):  # 페이지 1부터 50까지 반복
        url = f"https://sukebei.nyaa.si/?f=0&c=2_2&q=&s=seeders&o=desc&p={page}"
        response = requests.get(url, proxies=proxies)
        html = BeautifulSoup(response.text, "html.parser")
        trs = html.select("tr.success")

        magnets = [tr.select_one("a[href^='magnet']") for tr in trs]
        magnets = [magnet["href"] for magnet in magnets if magnet]

        for magnet in magnets:
            if magnet not in progressed_magnets:
                await download_torrent(magnet)
                save_progressed_magnet(magnet)
                progressed_magnets.add(magnet)


asyncio.run(main())
