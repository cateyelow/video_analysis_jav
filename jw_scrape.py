PLAY_BUTTON_CLASS = "jw-icon jw-icon-display jw-button-color jw-reset"
VIDEO_ELEMENT_CLASS = "jw-video jw-reset"
NO_VIDEO_MESSAGE = "No video in the current page"
import requests
from utils.crawler import Crawling
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


def scrape_video_no_protection(crawler: Crawling) -> str:
    """
    Gets video url directly from page. Raises a NoVideoAvailableException if no player is found
    """

    try:
        iframe = crawler.findElementSL(byType=By.TAG_NAME, value="iframe")
        crawler.driver.switch_to.frame(iframe)

        # clicks play to start video and load video url in the page
        play_button = crawler.findElementSL(
            byType=By.CSS_SELECTOR, value=f"div.{PLAY_BUTTON_CLASS}"
        )
        play_button.click()

        # gets video url from page once is loaded
        video_player_element = crawler.findElementBS(
            element="video", type="class", name=VIDEO_ELEMENT_CLASS
        )
        video_url = video_player_element["src"]
    except NoSuchElementException:
        raise Exception(NO_VIDEO_MESSAGE)

    return video_url


def scrape_video(crawler: Crawling) -> str:
    """
    Returns the url of the video in the current page.
    Raises a NoVideoAvailableException if no player is found
    """
    return scrape_video_no_protection(crawler=crawler)


def save_video_at(url: str, filename: str = None):
    """
    Saves the video in the given url
    """
    r = requests.get(url)

    if filename is None:
        filename = r.url.split("/")[-1]

    with open(filename, "wb") as out_file:
        out_file.write(r.content)

    return


def scrape_save_video(
    crawler: Crawling, filename: str = None, bypass_cloudflare: bool = True
):
    """
    Saves the video in the given url as filename after scraping it.
    Raises a NoVideoAvailableException if no player is found.
    If filename is None it is saved in the current directory with an automatically detected name.
    """
    video_url = scrape_video(crawler, bypass_cloudflare)
    save_video_at(video_url, filename)

    return
