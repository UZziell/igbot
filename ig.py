# aajeZzZzZzzzPlus
# This script finds clietns that didn't like top3 posts.
# --------------------------------------------------------------------------
# import json
import logging
import os
import pickle
import sys
from argparse import ArgumentParser
from datetime import datetime, timedelta
# from json import dump, load
from os.path import exists
from random import uniform, choice
from re import findall
from time import sleep

# import jdatetime
import pysftp
# import requests
# import selenium
# from bullet import Bullet, Check, YesNo, Input  # and etc...
from instaloader import (FrozenNodeIterator, Hashtag, Post, Profile,
                         instaloader, resumable_iteration)
from pyrogram import Client

# from requests import Timeout
# from selenium import webdriver
# from selenium.webdriver import ActionChains
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
# from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait

try:
    from my_secrets import *
except ImportError:
    sys.exit("Could not find and import secrets file!\nEXITED 1")

# parse command line arguments
parser = ArgumentParser()
parser.add_argument('-u', '--username', required=True,
                    help="Instagram username to use, REQUIRED")
parser.add_argument('-p', '--password', required=True,
                    help="Instagram password to use, REQUIRED")
args = parser.parse_args()

USERNAME = args.username
PASSWORD = args.password

# --------------------------------------------------------------------------
# Inputs (variables you can change)
ADMINS = ["Improve_2020", "Girlylife.mm", "ghazal.nasiriyan", "karmaroz1",
          "rozgoli53", "F.joharynad_2", "Farzaneh.jnad.55", "Shabahang_perfume", "Istanbul_va_bishtar"]

VIPS = ["solace.land"]

# HASHTAG = "TAG--" + jdatetime.datetime.now().strftime("%A-%d-%m-%Y--%H-%M")
HASHTAG = "#خدمات_انلاین_داریم"
TAGGED_PROFILE = "pishraftmikonim"
TOP3 = ['CIiH8varTJ7', 'CIiHl8ojPF2', 'CIiIO2iFCLc']
# --------------------------------------------------------------------------
# Constants (Variables you can't change unless you know what you are doing)
# PASSWORD = LOGIN_CREDS[USERNAME.lower()]
SESSION_FILE = f"sessions/{USERNAME}-SESSION"
WARN_HISTORY_FILE = "data/warn_history.pickle"
WARN_HISTORY_REMOTE_PATH = "/littleuzer/ig/warn_history.pickle"
LAST_WARN_LIST = "data/last_warning_list"
CLIENTS_LIST = "data/clients_list"
VIP_CLIENTS_LIST = "data/VIP_clients_list"
LAST_HASHTAG_STR = "data/last_hashtag_str"
COMPLETE_EXECUTION = False
PWD = os.getcwd()
FIREFOX_DRIVER_PATH = rf"{PWD}/drivers/geckodriver"
FIREFOX_PROFILE_PATH = r"/home/uzziel/.mozilla/firefox/euvy32zo.freshprofile"
LINKS_TEMP_FILE = "./temp/_links.pickle"
POSTERS_TEMP_FILE = "./temp/_posters.pickle"
HEADLESS = False
# --------------------------------------------------------------------------

logger = logging.getLogger()


def get_time():
    return datetime.now().strftime("%d-%m-%Y--%H-%M")


def setup_logging():

    # disable loggin of pyrogram except for errors
    logging.getLogger('pyrogram').setLevel(logging.ERROR)

    global logger
    now = get_time()

    logFormatter = logging.Formatter(
        "[%(asctime)s]  %(levelname)s - %(message)s")
    logFormatter.datefmt = "%H:%M:%S"
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # INFO - log file handler
    fileHandler = logging.FileHandler(
        f"logs/{now}.log", mode='a', encoding="utf-8")
    fileHandler.setFormatter(logFormatter)
    fileHandler.setLevel(logging.INFO)
    logger.addHandler(fileHandler)

    # Debug - log file handler
    fileHandlerDBG = logging.FileHandler(
        f"logs/{now}.log.debug", mode='a', encoding="utf-8")
    fileHandlerDBG.setFormatter(logFormatter)
    fileHandlerDBG.setLevel(logging.DEBUG)
    logger.addHandler(fileHandlerDBG)

    # console log stream hanlder
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.setLevel(logging.INFO)
    logger.addHandler(consoleHandler)


def dump_to_file(obj, file_path):
    with open(file_path, "wb") as wf:
        pickle.dump(obj, wf)
    logger.debug(f"dumped {obj} to file {file_path}")


def load_from_file(file_path):
    with open(file_path, "rb") as rf:
        obj = pickle.load(rf)
    logger.debug(f"Loaded object from file '{file_path}'")
    return obj


def remove_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.debug(f"Removed file '{file_path}'")


def telegram_send(user_id, header, message):
    "Parse message and devide to chunks then send to user_id"
    if isinstance(message, str):
        message = message.splitlines()

    split = [f"#{header} <b>{HASHTAG}</b> 👇🏼\n"]
    msg = ""
    for i, line in enumerate(message):
        msg += line + "\n"

        if i != 0 and i % 150 == 0:
            split.append(msg)
            msg = ""

    split.append(msg)

    # print(split)
    # with Client("sessions/pyrog.session", APP_ID, API_HASH, proxy=dict(hostname='127.0.0.1', port=9050)) as app:
    with Client("sessions/pyrog.session", APP_ID, API_HASH) as app:
        for msg in split:
            if msg != "\n" and msg != "":
                app.send_message(user_id, msg, parse_mode="html")


def telegram_send_gif(user_id):
    with Client("sessions/pyrog.session", APP_ID, API_HASH, proxy=dict(hostname='127.0.0.1', port=9050)) as app:
        # messages = app.get_history(-1001300601863)
        # gif = choice(messages)
        # app.forward_messages(chat_id=user_id, from_chat_id=-
        #                       1001300601863, message_ids=gif.message_id, as_copy=True)
        for i in range(0,10):
            try:
                gif_id = choice(range(2, app.get_history_count(chat_id=-1001300601863)))
                app.forward_messages(chat_id=user_id, from_chat_id=-1001300601863, message_ids=gif_id, as_copy=True)
                break
            except Exception:
                pass


def instaloader_init():
    # Get instance
    L = instaloader.Instaloader(sleep=True, download_pictures=False, post_metadata_txt_pattern="",
                                download_geotags=False, save_metadata=False,
                                download_comments=False, download_videos=False, download_video_thumbnails=False,
                                rate_controller=lambda ctx: instaloader.RateController(ctx))

    if not exists(SESSION_FILE):
        logger.info(f"Logging-in with account '{USERNAME}'...")
        L.login(USERNAME, PASSWORD)        # (login)
        L.save_session_to_file(filename=SESSION_FILE)
        # L.interactive_login(USER)      # (ask password on terminal)

    else:
        L.load_session_from_file(USERNAME, SESSION_FILE)

    return L


def get_followings(usernames, igloader):
    """find followings of admin users (subscribed users and VIP users)"""
    followings = []

    logger.info(f"Fetching {usernames} followees...")

    try:
        for username in usernames:
            profile = Profile.from_username(igloader.context, username)
            print(f"Fetching {username} followings...")
            for followee in profile.get_followees():
                followings.append(str(followee.username).lower())

    except instaloader.QueryReturnedBadRequestException as e:
        remove_file(SESSION_FILE)
        logger.exception(f"Exception details:\n {e}")
        logger.error(
            f"Bad Request Exception. Probably the account '{USERNAME}' was limited by instagram.\n\
                    To solve this: First try to *(solve captcha)* from instagram web and *(verify phone number)* and change password if required.\n")
        telegram_send(TELEGRAM_ID, "Account limited",
                      f"Account {USERNAME} was limited, solve the captcha and run again.")

    return list(set(followings))


def get_hashtag_posters(hashtag, loader):
    "Find posts from hashtag"
    # ITTERATOR_TEMP = "temp/frozenNodeIterator.pickle.tmp"
    # POSTERS_TEMP = "temp/posters.pickle.tmp"
    posters = []

    if "#" in hashtag:
        hashtag = hashtag.replace("#", "")

    logger.info(
        f"Finding posts with hashtag '{hashtag}'. This will take some time to complete! (70-95 minutes for ~800 posts)")

    post_iterator = Hashtag.from_name(loader.context, hashtag).get_posts()

    # try:
    for post in post_iterator:
        try:
            sleep(round(uniform(3.000, 7.000), 3))
            posters.append(post.owner_username)
            print(post.owner_username, "\t", post.date)
            if len(posters) % 50 == 0:
                print(
                    f"\t\t\t{get_time()}\tposts found so far: {len(posters)}")

        except instaloader.QueryReturnedBadRequestException as e:
            remove_file(SESSION_FILE)
            logger.exception(f"Exception details:\n {e}")
            logger.error(
                f"Bad Request Exception. Probably the account '{USERNAME}' was limited by instagram.\n\
                    To solve this: First try to *(solve captcha)* from instagram web and *(verify phone number)* and change password if required.\n")
            telegram_send(TELEGRAM_ID, "Account limited",
                          f"Account {USERNAME} was limited, solve captcha and when it was no longer limited, press enter")

            input(
                "ONLY when you SOLVED THE CAPTCHA and the account was NO LONGER LIMITED, 'press enter to continiue':  ")

            # You can also change -u command line argument to another account to fix this error")
            # sys.exit("Finally if none of above soleved the promlem, Call Support :) and give them this error log\nEXITED 1")

        except Exception as e:
            logger.error(
                f"Exception in fetching posts from instagram, EXITED\n Details: {e}")
            sys.exit(
                "Probably your internet was disconnected, 'Try to run again!!' \nEXITED 1")
    # except KeyboardInterrupt as e:
    #     logger.error(f"keyboardInterrupt, \n Details: {e}")
    #     sys.exit("User interrupted execution.\n EXITED 1")

    return posters


def firefox_builder():
    # binary = FirefoxBinary(FIREFOX_BINARY_PATH)
    profile = FirefoxProfile(FIREFOX_PROFILE_PATH)

    # apply the setting under (A) to ALL new windows (even script windows with features)
    profile.set_preference("browser.link.open_newwindow.restriction", 0)
    # open external links in a new window
    profile.set_preference("browser.link.open_newwindow.override.external", 2)
    # divert new window to a new tab
    profile.set_preference("browser.link.open_newwindow", 3)
    ##
    profile.set_preference("network.http.connection-timeout", 5)
    profile.set_preference("network.http.response.timeout", 5)
    profile.set_preference("dom.max_script_run_time", 5)
    # profile.set_preference("network.http.connection-retry-timeout", 15)
    ##
    # profile.update_preferences()
    opts = webdriver.firefox.options.Options()
    opts.headless = HEADLESS

    # browser = webdriver.Firefox(firefox_binary=binary, options=opts, firefox_profile=profile, executable_path=FIREFOX_DRIVER_PATH)
    browser = webdriver.Firefox(
        options=opts, firefox_profile=profile, executable_path=FIREFOX_DRIVER_PATH)
    browser.set_window_size(700, 700)
    browser.get("about:config")

    return browser


def sleep_with_print(seconds):
    for _ in range(seconds, 0, -1):
        print(f"{_} \r", end="")
        sleep(1)
    print("          ")


def get_hashtag_posters2(hashtag):
    """Find hashtag posters using webdriver from https://picuki.com"""
    posters = []
    links = {}
    double_check = {}

    if hashtag[0] == "#":
        hashtag = hashtag.replace("#", "")

    # if temp files existed, load and skip loading from websites
    if os.path.exists(POSTERS_TEMP_FILE) and os.path.exists(LINKS_TEMP_FILE):
        posters = load_from_file(POSTERS_TEMP_FILE)
        links = load_from_file(LINKS_TEMP_FILE)
        logger.info("Loaded links from file.")

    # if temp files didn't exist, load from website
    else:
        browser = firefox_builder()
        logger.info("Connect your VPN")
        sleep_with_print(10)
        # preventing browser.get hang
        # browser.set_script_timeout(0)
        # browser.set_page_load_timeout(5)

        logger.info(
            f"Finding posts with hashtag '{hashtag}'. This will take some time")
        reload = True
        while reload:
            try:
                browser.get(f"https://www.picuki.com/tag/{hashtag}")
                # browser.get(f"https://gramho.com/explore-hashtag/{hashtag}")
                reload = False

                assert "Instagram" in browser.title, "Could not load main page properly. Make sure VPN is connected"
            except selenium.common.exceptions.WebDriverException as e:
                if "Failed to decode response from marionette" in e.msg:
                    logger.exception(
                        "Something's wrong with browser, Is it even open?")
                    sys.exit(1)
                else:
                    logger.error(
                        "Could not load posts page. Make sure VPN is connected. Retrying in...")
                    sleep_with_print(4)
            except Exception as e:
                logger.error(
                    "Could not load posts page. Make sure VPN is connected. Retrying...")
        # find total number of posts
        total_post_element = browser.find_element_by_css_selector(
            "html body div.wrapper div.content div.content-header.tag-page.clearfix div.content-title div.content-subtitle")
        total_posts = int(total_post_element.text.split(" ")[0])
        logger.info(f"Total posts in theory = {total_posts}")

        # Scroll down to load all the posts
        body_element = browser.find_element_by_tag_name('body')
        for _ in range(1, int(total_posts / 10)+1):
            print(
                f"Loading more posts. Attempt {_}/{int(total_posts / 10)}\r", end="")
            browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            sleep(1)
            for _ in range(0, 15):
                body_element.send_keys(Keys.ARROW_UP)
            sleep(3)
            # body_element.send_keys(Keys.END)
            # sleep(5)
            # body_element.send_keys(Keys.END)
            # body_element.send_keys(Keys.ARROW_UP)
            # body_element.send_keys(Keys.HOME)
            # sleep(0.3)
        # save post link to `links`
        posts_elements = browser.find_elements_by_css_selector(
            "html body div.wrapper div.content.box-photos-wrapper ul.box-photos.clearfix li div.box-photo div.photo a")
        for post in posts_elements:
            link = post.get_attribute("href")
            # visit status, True: link already visited - False: link not visited
            links.setdefault(link, False)

        # Save loaded posts to file
        dump_to_file(links, LINKS_TEMP_FILE)
        dump_to_file(posters, POSTERS_TEMP_FILE)
        browser.quit()

    logger.info(f"Total posts found in action: '{len(links)}'")
    while False in links.values():  # while there is a link that is not visited:
        with requests.session() as session:  # open a requests.session
            for link, visited in links.items():
                if not visited:
                    try:
                        # response = requests.get(link, timeout=5)
                        response = session.get(link, timeout=5)  # get the link
                        if response.status_code == 404:
                            double_check.setdefault(link, 0)
                            double_check[link] += 1
                            logger.error(
                                f"Post not found '{link}', double_check status: {double_check[link]}/3")
                            if double_check[link] == 3:
                                logger.info(
                                    f"Marking link '{link}' as visited after three 404 responses.")
                                links[link] = True
                        elif response.status_code == 403:
                            logger.error(
                                "Forbidden 403, try changing your vpn, resting for 1 minute... (Disconnect/Connect your vpn dude)")
                            sleep_with_print(30)
                        elif response.status_code == 200:  # if the status code was 200, grab the username
                            username = findall(
                                "@[a-zA-Z0-9_.]*", response.text)
                            # username without the beginning @
                            posters.append(username[0][1:])
                            print(username[0])
                            links[link] = True
                    except KeyboardInterrupt:
                        dump_to_file(links, LINKS_TEMP_FILE)
                        dump_to_file(posters, POSTERS_TEMP_FILE)
                        logger.info("Keyboard Interrupt!")
                        sys.exit(1)
                    except (ConnectionError, Timeout):
                        logger.error(
                            "Connection Timeout or Error, Check VPN. Retrying in...")
                        sleep_with_print(5)
                    except Exception as e:
                        dump_to_file(links, LINKS_TEMP_FILE)
                        dump_to_file(posters, POSTERS_TEMP_FILE)

                    # Rest
                    if posters and len(posters) % 50 == 0:
                        print(
                            f"\t\t\t{get_time()}\tPosts so far: {len(posters)}, Resting 1 minute...")
                    #     sleep_with_print(60)
                    # elif posters and len(posters) % 20 == 0:
                    #     print("\t\t\tResting for 1/2 minute...")
                    #     sleep_with_print(30)

    # Double check links and remove temporary files if all links are visited
    for link, visited in links.items():
        if not visited:
            logger.info(f"link '{link}' is not visited yet.")
    if not (False in links.values()):
        remove_file(POSTERS_TEMP_FILE)
        remove_file(LINKS_TEMP_FILE)

    return posters


def get_hashtag_posters3(hashtag):
    posters = []
    links = {}
    total_posts = 600

    if "#" in hashtag:
        hashtag = hashtag.replace("#", "")

    browser = firefox_builder()
    logger.info("Connect your VPN")
    sleep_with_print(10)

    logger.info(
        f"Finding posts with hashtag '{hashtag}'. This will take some time")
    reload = True
    while reload:
        try:
            # find total number of posts
            browser.get(f"https://www.picuki.com/tag/{hashtag}")
            total_post_element = browser.find_element_by_css_selector(
                "html body div.wrapper div.content div.content-header.tag-page.clearfix div.content-title div.content-subtitle")
            total_posts = int(total_post_element.text.split(" ")[0])
            logger.info(f"Total posts in theory = {total_posts}")

            browser.get(f"https://www.stalkhub.com/tag/{hashtag}/")
            reload = False

            assert "Instagram" in browser.title, "Could not load main page properly. Make sure VPN is connected"
        except selenium.common.exceptions.WebDriverException as e:
            if "Failed to decode response from marionette" in e.msg:
                logger.exception(
                    "Something's wrong with browser, Is it even open?")
                sys.exit(1)
            else:
                logger.error(
                    "Could not load posts page. Make sure VPN is connected. Retrying in...")
                sleep_with_print(4)
        except Exception as e:
            logger.error(
                "Could not load posts page. Make sure VPN is connected. Retrying...")

    browser.find_element_by_css_selector(
        ".search-area > form:nth-child(1) > input:nth-child(1)").send_keys(hashtag)
    browser.find_element_by_partial_link_text("Tags").click()
    browser.find_element_by_partial_link_text(hashtag).click()

    # top_posts = browser.find_element_by_css_selector(
    #     "html.wf-roboto-n4-active.wf-roboto-n5-active.wf-roboto-n7-active.wf-roboto-n9-active.wf-active body div.general-card-list.hastag-ranked-card-list div.container")
    # top_posters = top_posts.find_elements_by_class_name("user-name")

    # Scroll down to load all the posts
    for _ in range(1, int(total_posts / 10)+1):
        print(
            f"Loading more posts. Attempt {_}/{int(total_posts / 10)}\r", end="")
        height = browser.execute_script("return document.body.scrollHeight")
        scroll_position = browser.execute_script("return window.scrollY")

        while scroll_position < height - 1500:
            browser.execute_script("window.scrollBy(0,700)")
            sleep(round(uniform(1.000, 1.500), 3))
            scroll_position = browser.execute_script("return window.scrollY")

        load_more_btn = browser.find_element_by_css_selector(
            "html.wf-roboto-n4-active.wf-roboto-n5-active.wf-roboto-n7-active.wf-roboto-n9-active.wf-active body div#getRecentData.general-card-list.load-more-area div.container div.button-area button#loadMoreButton.next-button")

        ActionChains(browser).move_to_element(load_more_btn).click().perform()
        sleep(4)

    posts_elements = browser.find_elements_by_css_selector(
        "html body div.wrapper div.content.box-photos-wrapper ul.box-photos.clearfix li div.box-photo div.photo a")
    for post in posts_elements:
        link = post.get_attribute("href")
        # visit status, True: link already visited - False: link not visited
        links.setdefault(link, False)

    browser.quit()

    return posters


def get_tagged_posters(username, loader):
    """Find posters that tagged a username"""
    ITTERATOR_TEMP = "temp/frozenNodeIterator.pickle.tmp"
    POSTERS_TEMP = "temp/posters.pickle.tmp"
    posters = []

    logger.info(
        f"Finding posts that user '{username}' was tagged in. This will take some time to complete! (25-35 minutes for every ~500 posts)")

    profile = Profile.from_username(loader.context, username)
    post_iterator = profile.get_tagged_posts()

    if exists(ITTERATOR_TEMP):
        loded_itr = load_from_file(ITTERATOR_TEMP)
        posters = load_from_file(POSTERS_TEMP)
        logger.info(
            f"Loaded post-itterator and {len(posters)} posts from file, continuing...")
        post_iterator.thaw(loded_itr)

    print("TYPE: ", type(post_iterator.freeze()))
    try:
        for post in post_iterator:
            sleep(round(uniform(1.000, 3.000), 3))
            posters.append(post.owner_username)
            print(post.owner_username, "\t", post.date)
            if len(posters) % 50 == 0:
                print(
                    f"\t\t\t{get_time()}\tposts found so far: {len(posters)}")
    except KeyboardInterrupt as e:
        dump_to_file(post_iterator.freeze(), ITTERATOR_TEMP)
        dump_to_file(posters, POSTERS_TEMP)

        logger.error(
            f"keyboardInterrupt, dummped posters found so far to file. EXITED\n Details: {e}")
        sys.exit("User interrupted execution.\n EXITED 1")
    except instaloader.QueryReturnedBadRequestException as e:
        dump_to_file(post_iterator.freeze(), ITTERATOR_TEMP)
        dump_to_file(posters, POSTERS_TEMP)
        remove_file(SESSION_FILE)

        logger.exception(f"Exception details:\n {e}")
        logger.error(
            f"Bad Request Exception. Probably the account '{USERNAME}' was limited by instagram.\n\
                To solve this: First try to *(solve captcha)* from instagram web and *(verify phone number)* and change password if required.\n\
                You can also change -u command line argument to another account to fix this error")
        sys.exit("\nEXITED 1")

    except Exception as e:
        dump_to_file(post_iterator.freeze(), ITTERATOR_TEMP)
        dump_to_file(posters, POSTERS_TEMP)

        logger.error(
            f"Exception in fetching posts from instagram, EXITED\n Details: {e}")
        sys.exit(
            "Probably your internet was disconnected, 'Try to run again!!' \nEXITED 1")

    remove_file(ITTERATOR_TEMP)
    remove_file(POSTERS_TEMP)
    return posters


def get_post_likers(shortcode, loader):
    try:
        post = Post.from_shortcode(loader.context, shortcode)
    except KeyError as e:
        logger.exception(f"Exception details: {e}")
        logger.error(
            f"HUMAN READABLE ERROR LOG:\n\
                Could not create post from shortcode '{shortcode}'.\n\
                    Make sure:\n\t-the post is not deleted and \n\t-there is no typo in the shortcode \n then try again")
        sys.exit("Exited 1")

    except instaloader.QueryReturnedBadRequestException as e:
        remove_file(SESSION_FILE)
        logger.exception(f"Exception details: {e}")
        logger.error(f"HUMAN READABLE ERROR LOG:\n\
                Well, I guess Instagram limited the Account '{USERNAME} again.\n\
                Solve the captcha from instagram web and make sure the password is correct.\n\
                If the problem persisted remove session file '{SESSION_FILE}'.")

        telegram_send(TELEGRAM_ID, "Account limited",
                      f"Account {USERNAME} was limited while fetching {HASHTAG} posts,\
                               solve captcha and and run the code again. it will resume automatically")

        sys.exit("DO ABOVE ADN RUN AGIAN.\nEXITED 1")

    post_likers = []
    for liker_profile in post.get_likes():
        post_likers.append(liker_profile.username.lower())

    return post_likers


def find_assholes():
    """Finds clients that didn't like top posts. First loads or update clients list.
    Then finds all posts with given hashtag. Then finds top-posts likers. 
    Finally finds which client didn't like top-posts at all."""

    bitches = []    # users that posted the hashtag but aren't clients
    cheaters = []   # hastag_posters with more than one post
    clients_likes = {}  # saving client like per post to find assholes
    assholes = []  # Assholes, clients that didn't like top posts

    logger.info(f"Current datetime: {get_time()}")
    logger.debug(f"Inputs: \n\tHashtag: '{HASHTAG}'\n\tAdmins: {ADMINS}\n\tVIP-Admins: {VIPS}\n\
        \tTop Posts: {TOP3}\n\tAccount: '{USERNAME}'\n\tTagged Profile: '{TAGGED_PROFILE}'")

    # fetch all clients from ADMINS's followings
    clients = load_or_update(ADMINS + VIPS, CLIENTS_LIST)
    logger.info(f"Total '{len(clients)}' subscribed clients found.")
    logger.debug(f"Clients:\n\t{sorted(clients)}\n\n")

    L = instaloader_init()

    # fetch hashtag posters from instagram or load from last unsuccessful execution
    if exists(POSTERS_TEMP_FILE+"_"):
        posters = load_from_file(POSTERS_TEMP_FILE+"_")
    else:
        posters = get_hashtag_posters(HASHTAG, L)
        # posters = get_tagged_posters(TAGGED_PROFILE, L)
        # posters = get_hashtag_posters2(HASHTAG)
        dump_to_file(posters, POSTERS_TEMP_FILE+"_")

    logger.info(
        f"len(posters)={len(posters)} - len(set(posters))={len(set(posters))}")
    logger.debug(f"'{len(posters)}' posters:    {sorted(posters)}\n\n")

    total = len(posters)

    # find bitches and cheaters
    for poster in posters:
        if poster not in clients:
            bitches.append(poster)
            # posters.remove(poster)   # remove bitches from posters
        if posters.count(poster) > 1:
            cheaters.append(poster)
            posters.remove(poster)

    # remove dulicate usernames
    posters = list(set(posters))
    logger.info(
        f"'{len(posters)}' unique posts from clients:\t{sorted(posters)}")

    # find likers of every post and mark those who didn't like them
    logger.info(f"Fetching posts {TOP3} likes from instagram...")
    for shortcode in TOP3:
        post_likers = get_post_likers(shortcode, L)
        client_post_likers = [
            client for client in post_likers if client in posters]
        logger.info(f"  post '{shortcode}' had {len(post_likers)} likes; "
                    f"'{len(client_post_likers)}' of which were client ~ {int((len(client_post_likers)/len(post_likers))*100)}%")
        logger.debug(f"likes => {sorted(post_likers)}\n")

        # find which client didn't like current post and add one to clients_likes[client] dict
        for user in posters:
            if user not in post_likers and user+".hami2020" not in post_likers and user+".lrs" not in post_likers and user+".ikiu" not in post_likers:
                clients_likes.setdefault(user, 0)
                clients_likes[user] += 1
                if clients_likes[user] == len(TOP3):
                    assholes.append(user)
        sleep(5)

    WIDTH = 140
    ASTERISK = "*"
    ASTERISK_COUNT = 50
    SPACE = " "
    SPACE_COUNT = int((WIDTH - ASTERISK_COUNT*2 - 14)/2)

    report = f"\
        \n{ASTERISK*WIDTH}\
        \n{ASTERISK*WIDTH}\
        \n{ASTERISK*ASTERISK_COUNT}{SPACE*SPACE_COUNT}    REPORT    {SPACE*SPACE_COUNT}{ASTERISK*ASTERISK_COUNT}\
        \n{ASTERISK*ASTERISK_COUNT : <{ASTERISK_COUNT}}{HASHTAG : ^{WIDTH-ASTERISK_COUNT*2}}{ASTERISK*ASTERISK_COUNT}\
        \n{ASTERISK*ASTERISK_COUNT : <{ASTERISK_COUNT}}{total : ^{WIDTH-ASTERISK_COUNT*2}}{ASTERISK*ASTERISK_COUNT}\
        \n{ASTERISK*WIDTH}\
        \n{ASTERISK*WIDTH}\
        \n{ASTERISK*ASTERISK_COUNT}{SPACE*SPACE_COUNT}'{len(set(bitches)): >3}' Bitches {SPACE*SPACE_COUNT}{ASTERISK*ASTERISK_COUNT}\n{sorted(bitches)}\
        \n{ASTERISK*WIDTH}\
        \n{ASTERISK*ASTERISK_COUNT}{SPACE*SPACE_COUNT}'{len(set(cheaters)): >3}' Cheaters{SPACE*SPACE_COUNT}{ASTERISK*ASTERISK_COUNT}\n{sorted(cheaters)}\
        \n{ASTERISK*WIDTH}\
        \n{ASTERISK*ASTERISK_COUNT}{SPACE*SPACE_COUNT}'{len(assholes): >3}' Assholes{SPACE*SPACE_COUNT}{ASTERISK*ASTERISK_COUNT}\n{sorted(assholes)}\
        \n{ASTERISK*WIDTH}\n"

    logger.info(report)
    # msg_cheaters = "CHEATERS: \n\n"
    # for cheater in cheaters:
    #     msg_cheaters += (cheater + "\n")

    telegram_send(
        TELEGRAM_ID, f"BITCHES '{len(set(bitches))}'", list(set(bitches)))
    telegram_send(
        TELEGRAM_ID, f"CHEATERS '{len(set(cheaters))}'", list(set(cheaters)))

    # CLEAN UP
    # dump last warn list and hashtag to file
    dump_to_file(assholes, LAST_WARN_LIST)
    dump_to_file(HASHTAG, LAST_HASHTAG_STR)
    # dump report to file
    with open(f"logs/report-{HASHTAG}.txt", "a") as af:
        af.write(report)

    # remove temp posters
    remove_file(POSTERS_TEMP_FILE+"_")

    return assholes


def sftp_client(mode, local_file, remote_file):

    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    with pysftp.Connection(host=SFTP["server"], username=SFTP["username"], password=SFTP["passwd"], port=SFTP["port"], cnopts=cnopts) as sftpp:
        logger.info(
            f"Connection succesfully established to sftp server '{SFTP['server']}'")

        if mode == "get":
            if sftpp.exists(remote_file) and sftpp.stat(remote_file).st_size > 0:
                # if local file exists, only replace remote with local if remote file is bigger in size
                if (exists(local_file) and sftpp.stat(remote_file).st_size > os.path.getsize(local_file)) or not exists(local_file):
                    sftpp.get(remote_file, local_file)
                    logger.info(
                        f"Pulled newest warning history file and saved to /data. Size = {sftpp.stat(remote_file).st_size} bytes")
            else:
                logger.info(
                    "Remote file didn't exist or was empty. Proceeding...")

        elif mode == "put":
            if exists(local_file) and os.path.getsize(local_file) > 0:
                # if remote file exists, only replace local file with remote file if local file is bigger in size
                if (sftpp.exists(remote_file) and os.path.getsize(local_file) > sftpp.stat(remote_file).st_size):
                    backupname = remote_file + \
                        f"-{get_time()}"
                    sftpp.rename(remote_file, backupname)
                    sftpp.put(local_file, remote_file)
                elif not sftpp.exists(remote_file):
                    sftpp.put(local_file, remote_file)
                logger.info(
                    f"Updated Warning history file and pushed to server successfully, Size = {sftpp.stat(remote_file).st_size} bytes")


def update_warndb(warned_clients):
    """creates(if not already existed) or updates the warned users dictionary"""

    try:  # try to fetch newest warn history from server
        sftp_client(mode="get", local_file=WARN_HISTORY_FILE,
                    remote_file=WARN_HISTORY_REMOTE_PATH)
    except Exception as e:
        logger.exception(e)
        logger.error(
            "Something went wrong while recieving last warning history file from server. Proceeding with local history file.")

    # Load or create obj and add new data to it
    if exists(WARN_HISTORY_FILE):
        # Update existing obj
        warn_dic = load_from_file(WARN_HISTORY_FILE)

    else:
        # Create a brand new obj
        warn_dic = {}

    for client in warned_clients:
        warn_dic.setdefault(client, set())
        if HASHTAG not in warn_dic[client] and HASHTAG != "":
            warn_dic[client].add(HASHTAG)

    # Create backup
    if exists(WARN_HISTORY_FILE):
        backupname = WARN_HISTORY_FILE + '.bak'
        if exists(backupname):
            os.remove(backupname)
        os.rename(WARN_HISTORY_FILE, backupname)

    # Save and put the updated file to server
    with open(WARN_HISTORY_FILE, "wb") as f:
        pickle.dump(warn_dic, f, protocol=4)
        logger.info("Warning history file updated.")

    try:
        sftp_client(mode="put", local_file=WARN_HISTORY_FILE,
                    remote_file=WARN_HISTORY_REMOTE_PATH)
    except Exception as e:
        logger.exception(e)
        logger.error(
            "Something went wrong while pushing last warning history file to server. Keep local file safe")


def load_or_update(client_admins, c_file):
    """loads given admin's clients list from file or updates them from instagram. Used for clients and VIP clients"""
    # TODO: add time based decision of fetching or loading from file: DONE!

    update = False
    string = "clients"
    if "vip" in c_file.lower():
        string = "VIP " + string

    if exists(c_file):
        hour_ago = datetime.now() - timedelta(minutes=300)
        file_epoch = os.path.getmtime(c_file)
        file_mtime = datetime.fromtimestamp(file_epoch)
        if file_mtime > hour_ago:  # if the file was last modified during the last hour, load it
            clients = load_from_file(c_file)
            logger.info(f"Loaded {len(clients)} {string} from file.")
            if len(clients) == 0:    # if the loaded file was empty and didn't have any client
                logger.info("Loaded file was empty. Mandatory update")
                update = True
        else:  # if the file was not updated in the last hour, then update from instagram
            update = True
    else:
        logger.info(f"{c_file} file was not found. Mandatory update")
        update = True

    if update:
        L = instaloader_init()
        logger.info(f"Fetching {string} from instagram...")
        clients = get_followings(client_admins, L)
        dump_to_file(clients, c_file)
        logger.info(f"Fetched '{len(clients)}' {string} and saved to file.")

    return clients


def print_warning_history():
    vip_clients = load_or_update(VIPS, VIP_CLIENTS_LIST)
    warn_dic = load_from_file(WARN_HISTORY_FILE)
    hashtags = set()

    print("\nWarning history since Azaaal(ازل) (VIP clients excluded - sorted): ")

    # for client in sorted(warn_dic, key=lambda client: len(warn_dic[client]), reverse=True):
    for client in sorted(warn_dic):
        if client not in vip_clients:  # and if len(warn_dic[client]) > 1:
            for hashtag in warn_dic[client]:
                hashtags.add(hashtag)
            # print(f"{client : <30}{'+' * (len(warn_dic[client])-1) : ^13}{warn_dic[client]} ** VIP ** ")
            print(f"{client} {'+' * (len(warn_dic[client])-1)}")

    print(
        f"\nThis history included '{len(warn_dic)}' clients and '{len(hashtags)}' hashtags: {sorted(hashtags)}")


def print_last_warn():
    global HASHTAG
    vip_clients = load_or_update(VIPS, VIP_CLIENTS_LIST)
    warn_dic = load_from_file(WARN_HISTORY_FILE)
    # last_hashtag = load_from_file(LAST_HASHTAG_STR)
    HASHTAG = load_from_file(LAST_HASHTAG_STR)
    last_warn_list = load_from_file(LAST_WARN_LIST)

    # fancy = f"\nFancy little list of to-be-warned clients (assholes) for hashtag '{last_hashtag}' excluding VIPs:\n"
    fancy = "\n"
    psign = "+"
    for client in sorted(last_warn_list):
        if client not in vip_clients:
            fancy = fancy + \
                f"{client} {psign * ((len(warn_dic[client])-1) % 4)}\n"
            # if client in warn_dic.keys():
            #     print("+" * (len(warn_dic[client])-1), end='')
            # print("")

    print(fancy)

    if COMPLETE_EXECUTION:  # write fancy list to report file if find assholes function was called before
        with open(f"logs/report-{HASHTAG}.txt", "a") as af:
            af.write(fancy)

        telegram_send(TELEGRAM_ID, "ASSHOLES", fancy)
        telegram_send_gif(TELEGRAM_ID)
        assholes_cout = len(fancy.split('\n'))
        telegram_send(DUDE, "ALL COOL", f"{len(last_warn_list)}, fancy={assholes_cout}")


def update_warndb_manually():
    """updates warning history file manually from user input list of clients and a hashtag based on current time."""
    tobe_warned_manual = []
    print(
        "Enter/Paste your list of clients (one user per line). Ctrl-D or Ctrl-Z ( windows ) to save it.\r\n")
    usr_input_list = sys.stdin.readlines()

    for i in usr_input_list:
        print(i.strip().split(" ")[0])
        if i.strip() != '' and i != "\n":
            tobe_warned_manual.append(i.strip().split(" ")[0])

    print(f"\n\n - Your INPUT:\n {tobe_warned_manual}")
    continuee = input(
        f"\n- Are you sure you want to update warning history file with these '{len(tobe_warned_manual)}' clients?\
            \n\t1> yes, Update\
            \n\t2> no,  Exit\
            \nYour choice: ")
    if continuee.lower() == "1":
        logger.info(
            f"Going to update history file with hashtag '{HASHTAG}' and these '{len(tobe_warned_manual)}' clients:\n {tobe_warned_manual}")
        update_warndb(tobe_warned_manual)

    elif continuee.lower() == "2":
        print("Cool. Job canceled and didn't update. Bye.")

    # Update last warn file
    old_last_warning_list = load_from_file(LAST_WARN_LIST)
    new_last_warning_list = old_last_warning_list.extend(tobe_warned_manual)
    dump_to_file(new_last_warning_list, LAST_WARN_LIST)


def menu():
    global HASHTAG, COMPLETE_EXECUTION, TAGGED_PROFILE
    while True:
        choices = ["1> Find Assholse\t(Find clients that didn't like posts of a certain hashtag)", "2> Print Warning History\t(History of asshole clients from the beginning of the time)",
                   "3> Print Last Assholes\t(Print asshole clients (one in each line) of the last search)", "4> Manually Update Warning History (update warning history file manually from a list of input clients)", "5> Exit"]

        print("Main Menu:")
        for choice in choices:
            print(f"  {choice}")
        user_choice = input("Enter number of the job you want to do: ")

        if user_choice == "1":
            COMPLETE_EXECUTION = True
            # input_tag = input(
            #     f"\n - Enter a tagged user (press enter to skip and use '{TAGGED_PROFILE}' as tagged user): ")
            input_tag = input(
                f"\n - Enter n new hashtag (or press enter to skip and use '{HASHTAG}' as tagged user): ")
            if input_tag != "":
                HASHTAG = input_tag.strip()

            nth = {1: "first", 2: "second", 3: "third"}
            for i in range(0, 3):
                try:
                    post_link = input(
                        f" -- Enter {nth[i+1]} top-post link (press enter to skip and use '{TOP3[i]}' as {nth[i+1]} link): ")
                    if post_link != "":
                        TOP3[i] = post_link.split("/")[4]
                except IndexError:
                    print(
                        "Please enter a link that follows this format: https://instagram.com/p/SHORTCODE/...")
                    sys.exit("Exited 1, Invalid user input!")

            print(f"Current Inputs: \n\
            \tHashtag: '{HASHTAG}'\n\
            \tAdmins: {ADMINS}\n\
            \tVIP-Admins: {VIPS}\n\
            \tTop Posts: {TOP3}\n\
            \tAccount: '{USERNAME}'\n\
            \tTgged profile: '{TAGGED_PROFILE}'")
            print("")

            continuee = input(
                "Are these inputs correct? \n\t1> yes, Proceed\n\t2> no, Exit\nYour choice: ")
            if continuee.lower() == "1" or continuee == "\n":
                # setup_logging()
                assholes = find_assholes()
                update_warndb(assholes)

                print_last_warn()
                # break

            elif continuee.lower() == "2":
                print("\nSo edit the inputs and re-run the script! (To edit the Account or Admins or VIP-Admins, manually edit the source file.)")
                # break
            else:
                sys.exit("Exited 1, Invalid user input!")

        elif user_choice == "2":
            print_warning_history()

        elif user_choice == "3":
            print_last_warn()

        elif user_choice == "4":
            HASHTAG = f"Screenshot_Warning_{get_time()}"
            update_warndb_manually()

        elif user_choice == "5":
            print("Cool!! Adios.")
            break

        else:
            print(
                f"Your choice should be between 1-{len(choices)}! Run the script again and choose wisely.")

        print("")
        for t in range(3, 0, -1):
            print(f"\rReloading main menu... {t}", end="")
            sleep(1.5)
        print("\n"*4)


if __name__ == "__main__":
    setup_logging()
    menu()

    # # MANUALLY UPDATE WARN_HISTORY FROM FILE
    # with open("manual", "r") as rf:
    #     lizt = rf.readlines()
    #     tobe_warnned = []
    #     HASHTAG = ""
    #     for i in lizt:
    #         if "#" in i:
    #             HASHTAG = i.strip()[1:]
    #         elif i != "\n":
    #             tobe_warnned.append(i.strip().split()[0])
    #         elif i == "\n":
    #             print(f"hashtag: '{HASHTAG}'\n  {tobe_warnned}\n\n")
    #             update_warndb(tobe_warnned)
    #             tobe_warnned = []
    #             HASHTAG = ""

    # bitches = []
    # cheaters = []
    # assholes = []

    # with open(WARN_HISTORY_FILE, 'rb') as dbfile:
    #     warn_dic = pickle.load(dbfile)
    # for client in sorted(warn_dic):
    #         print(client, warn_dic[client])

    # main_menu = Bullet(prompt="Choose one and press enter:",
    #                    choices=choices)  # Create a Bullet or Check object
    # result = main_menu.launch()  # Launch a prompt

    # if result == choices[1]:
    #     print_warning_history()
    # elif result == choices[0]:
