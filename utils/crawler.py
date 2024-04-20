from collections import defaultdict
import os
import platform
import shutil
from bs4 import BeautifulSoup as bs
import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from fake_useragent import UserAgent

from random import choice, randrange, random
import time
import json
import gc
from pathlib import Path
from utils.get_chrome_version import get_chrome_version

from utils.uc_proxy import proxies
import threading

from selenium_profiles.webdriver import Chrome
from selenium_profiles.profiles import profiles
import seleniumwire.undetected_chromedriver as uc


import chromedriver_autoinstaller


class DriverInitializer(threading.Thread):
    def __init__(
        self, options, seleniumwire_options, version_main, randomMobileEmulation=False
    ):
        super().__init__()
        self.options = options
        self.seleniumwire_options = seleniumwire_options
        self.version_main = version_main
        self.randomMobileEmulation = randomMobileEmulation
        self.driver = None
        self.exception = None

    def run(self):
        try:
            profile = None
            if self.randomMobileEmulation:
                profile = defaultdict(lambda: None)
                with open("./mobile_profiles/mobile_emulation.json", "r") as f:
                    profile.update(choice(json.load(f)["Android"]))

            # Here, you check if version_main is set and use it to install the specific version of ChromeDriver
            if self.version_main:
                execute_path = chromedriver_autoinstaller.install(
                    True, self.version_main
                )
            else:
                execute_path = chromedriver_autoinstaller.install()

            if self.randomMobileEmulation:
                self.driver = Chrome(
                    options=self.options,
                    seleniumwire_options=self.seleniumwire_options,
                    profile=profile,
                    uc_driver=True,
                    executable_path=execute_path,
                )
            else:
                self.driver = uc.Chrome(
                    options=self.options,
                    seleniumwire_options=self.seleniumwire_options,
                    executable_path=execute_path,
                    version_main=self.version_main,
                )
        except WebDriverException as e:
            self.exception = e


class Crawling:
    def __init__(
        self,
        url,
        headless=False,
        isProxy=True,
        proxy=None,
        step=0,
        useProfile=False,
        randomUserAgent=False,
        randomMobileUserAgent=False,
        randomMobileEmulation=False,
    ):
        self.headless = headless
        self.url = url
        self.driver = None
        self.isProxy: bool = isProxy
        self.proxy: str = proxy
        self.useProfile = useProfile
        self.randomUserAgent = randomUserAgent
        self.randomMobileUserAgent = randomMobileUserAgent
        self.randomMobileEmulation = randomMobileEmulation
        self.step = step
        self.soup = None
        self.retries = 3

    def load_proxy(self) -> str:
        """Load a random proxy from the file."""
        if self.proxy:
            print(f"proxy: {self.proxy}")
            return self.proxy

        with open("iplist.txt", "r") as f:
            proxies = f.read().splitlines()

        SIZE_PER_STEP = 5
        proxy = proxies[
            randrange(self.step * SIZE_PER_STEP, (self.step + 1) * SIZE_PER_STEP)
        ]
        print(f"proxy: {proxy}")
        return proxy

    def getRandomMobileUserAgent(self):
        mobile_list = [
            "Mozilla/5.0 (Linux; Android 8.0.0; SM-G930K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 9; SM-N950U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 8.1.0; Pixel 2 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.105 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 7.1.1; Moto G (5S) Plus) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 6P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 5.1.1; SM-G928X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 4.4.4; Nexus 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Mobile Safari/537.36",
        ]

        return choice(mobile_list)

    def startDriver(self):
        ua = UserAgent()
        userAgent = ua.random
        print(userAgent)

        PROXY = self.load_proxy()

        options = uc.ChromeOptions()
        seleniumwire_options = {
            "connection_keep_alive": False,
            "request_storage": "memory",
            "auto_config": True,
        }

        # Identify the largest drive on Windows
        if platform.system() == "Windows":
            drives = [
                f"{drive}:\\"
                for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                if os.path.exists(f"{drive}:\\")
            ]
            largest_drive = max(drives, key=lambda drive: shutil.disk_usage(drive).free)
            temp_path = os.path.join(
                largest_drive, "seleniumwire"
            )  # Use the largest drive for the temp path
        else:
            temp_path = "/seleniumwire"  # Set a custom path for Linux and macOS

        # Create the directory if it does not exist
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

        seleniumwire_options["request_storage_base_dir"] = temp_path

        if self.isProxy:
            seleniumwire_options["proxy"] = {
                "proxy": {
                    "http": f"http://{PROXY}",
                    "https": f"https://{PROXY}",
                    "no_proxy": "localhost,127.0.0.1",  # excludes
                },
            }
            options.add_argument(f"--proxy-server=http://{PROXY}")

        ip, port = PROXY.split(":")
        self.proxy = PROXY
        script_address = os.getcwd() + f"/temp/{ip}"
        if self.isProxy:
            proxies(
                username="",
                password="",
                endpoint=ip,
                port=port,
                path=script_address,
            )
            options.add_argument("--load-extension=" + script_address)

        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        if self.randomUserAgent:
            options.add_argument(f"user-agent={userAgent}")
        if self.randomMobileUserAgent:
            options.add_argument(f"user-agent={self.getRandomMobileUserAgent()}")

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        # options.add_argument("--dns-prefetch-disable")
        # options.add_argument("--disable-extensions")
        options.add_argument("--disable-application-cache")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")
        # Disable Features
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-prompt-on-repost")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        # Reduce Resources
        options.add_argument("--max-web-media-player-count=1")
        options.add_argument("--autoplay-policy=user-gesture-required")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-breakpad")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-domain-reliability")
        options.add_argument(
            "--disable-features=AudioServiceOutOfProcess,IsolateOrigins,site-per-process"
        )
        options.add_argument("--disable-print-preview")
        # Memory Management Flags
        options.add_argument("--process-per-tab")
        options.add_argument("--enable-strict-site-isolation")
        options.add_argument("--memory-pressure-off")
        # Optimize Cache and Storage
        options.add_argument("--media-cache-size=1")
        options.add_argument("--disk-cache-size=1")
        options.add_argument("--aggressive-cache-discard")
        options.add_argument("--disable-cache")
        options.add_argument("--disable-application-cache")
        # System-Level Optimizations
        # options.add_argument("--single-process")
        options.add_argument("--disable-threaded-animation")
        options.add_argument("--disable-threaded-scrolling")
        options.add_argument("--disable-checker-imaging")
        # Reduce Feature Usage
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-geolocation")
        options.add_argument("--disable-speech-api")
        options.add_argument("--disable-remote-fonts")

        # 위치 권한 요청 창에서 자동으로 거부를 누르도록 설정
        prefs = {"profile.default_content_setting_values.geolocation": 2}
        options.add_experimental_option("prefs", prefs)

        if self.useProfile:
            chrome_profile_dir = "chrome_profile_1"
            # Create empty profile to start with if it's not yet used
            if not os.path.isdir(chrome_profile_dir):
                os.mkdir(chrome_profile_dir)

            Path(f"{chrome_profile_dir}/First Run").touch()
            options.add_argument(f"--user-data-dir={chrome_profile_dir}/")

        version_main = int(get_chrome_version().split(".")[0])

        initializer = DriverInitializer(
            options,
            seleniumwire_options,
            version_main,
            randomMobileEmulation=self.randomMobileEmulation,
        )
        initializer.start()
        initializer.join(timeout=30)

        if initializer.is_alive():
            print("Initialization timed out")
            raise TimeoutError("Initialization timed out")
        else:
            if initializer.exception:
                print(f"Exception during initialization: {initializer.exception}")
            else:
                print("Initialization successful")
                self.driver = initializer.driver

        try:
            (
                self.driver.set_window_size(300, 300)
                if not self.headless and not self.randomMobileEmulation
                else None
            )
            # self.driver.minimize_window()
            self.driver.set_page_load_timeout(30)
            self.driver.get(self.url)
        except TimeoutException as ex:
            print(ex.Message)
            self.driver.refresh()
        except WebDriverException as e:
            if "net::ERR_TUNNEL_CONNECTION_FAILED" in str(
                e
            ) or "ERR_PROXY_CONNECTION_FAILED" in str(e):
                print(
                    "Proxy connection failed. Trying again with a different proxy or check your proxy settings."
                )
                self.step += 1
                self.load_proxy()
                self.restartDriver()
            else:
                print(f"WebDriver Exception: {e}")

    def quitDriver(self):
        if self.driver:
            self.driver.quit()
            self.cleanup()

    def restartDriver(self):
        self.step += 1
        if self.step > 200:
            self.step = 0
        self.quitDriver()
        self.startDriver()

    def moveDriver(self, url, intercept=None):
        retry = 0
        success = False
        while retry < self.retries and not success:
            try:
                self.url = url
                if intercept:
                    self.driver.request_interceptor = intercept
                self.driver.set_page_load_timeout(30)
                self.driver.get(self.url)
                time.sleep(1 + random())
                self.getBS()
                if "Cannot establish TLS" in self.soup.text:
                    print("Cannot establish TLS")
                    retry += 1
                else:
                    success = True
            except TimeoutException as ex:
                retry += 1
                print(ex.Message)
                self.driver.refresh()
            except WebDriverException as e:
                retry += 1
                if "net::ERR_TUNNEL_CONNECTION_FAILED" in str(e):
                    print(
                        "Proxy connection failed. Trying again with a different proxy or check your proxy settings."
                    )
                    self.restartDriver()
                else:
                    print(f"WebDriver Exception: {e}")
            except Exception as e:
                retry += 1
        self.driver.implicitly_wait(10)
        self.driver.requests.clear()

    def getBS(self):
        if self.soup:
            self.soup.decompose()
        self.soup = bs(self.driver.page_source, "html.parser")
        gc.collect()  # Invoke garbage collector

    def getJson(self):
        try:
            self.getBS()
            self.json = json.loads(self.soup.text)
            return self.json
        except:
            print(f"Extract JSON Error {self.soup.text}")
            self.restartDriver()

    def findElementsBS(self, element, type, name, recursive=True):
        self.getBS()
        # Check if the element exists
        if self.soup.find(element, {type: name}, recursive):
            self.elementsBS = self.soup.find_all(element, {type: name}, recursive)
            return self.elementsBS
        else:
            print(f"{type} {name} Element not found")
            return ""

    def findElementBS(self, element, type, name):
        self.getBS()
        if self.soup.find(element, {type: name}):
            self.elementBS = self.soup.find(element, {type: name})
            return self.elementBS
        else:
            print(f"{type} {name} Element not found")
            return ""

    def findElementsBS_target(self, target, element, type, name, recursive=True):
        try:
            self.elementsBS = target.find_all(element, {type: name})
            return self.elementsBS
        except:
            return None

    def findElementBS_target(self, target, element, type, name):
        try:
            self.elementBS = target.find(element, {type: name})
            return self.elementBS
        except:
            return None

    def findElementsSL(self, byType, value):
        try:
            self.elementsSL = self.driver.find_elements(byType, value)
            return self.elementsSL
        except:
            return None

    def findElementSL(self, byType, value):
        try:
            self.elementSL = self.driver.find_element(byType, value)
            return self.elementSL
        except:
            return None

    def getText(self, element) -> str:
        return element.text

    def getTexts(self, elements) -> str:
        text = ""
        for element in elements:
            text += element.text
        return text

    def click(self, element):
        element.click()

    def makeFilename(self):
        import uuid

        unique_filename = str(uuid.uuid4().hex)
        return unique_filename

    def imageDownload(self, imageUrls: list):
        from PIL import Image
        from io import BytesIO
        import os

        imageNames = []
        imageBytes = []
        if not os.path.exists("cache"):
            os.makedirs("cache")

        for url in imageUrls:
            file_name = self.makeFilename() + ".JPEG"
            file_path = os.path.join("cache", file_name)

            # Open the image link
            self.moveDriver(url)
            img = self.driver.find_element(By.CSS_SELECTOR, f'img[src="{url}"]')

            # Get the image as a binary
            image_binary = img.screenshot_as_png

            # Open the image using PIL
            image = Image.open(BytesIO(image_binary))

            # If the image mode is not 'RGB', convert it
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Resize the image to a smaller size while maintaining its aspect ratio
            max_size = (500, 500)
            image.thumbnail(max_size, Image.LANCZOS)

            # Save the resized image to an in-memory binary stream
            img_byte_array = BytesIO()
            image.save(img_byte_array, "JPEG", quality=80, optimize=True)

            imageNames.append(file_name)
            imageBytes.append(img_byte_array)
            # print(f"Downloaded and resized {file_name} to ./cache")
            time.sleep(1 + random())

        return imageNames, imageBytes

    def cleanup(self):
        self.driver.quit()
        self.soup.decompose() if self.soup else None
        self.soup = None
        gc.collect()


if __name__ == "__main__":
    url = "https://api.bunjang.co.kr/api/1/find_v2.json?page=0&order=date&req_ref=popular_category&n=10&version=4"
    driver = Crawling(url=url, isProxy=False, step=0)
    driver.startDriver()
    driver.getJson()
