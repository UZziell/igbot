import functools
import logging
import shutil
import sys
import json
import os
from os.path import exists
import random
from time import perf_counter, sleep

from instaloader import (FrozenNodeIterator, NodeIterator, Hashtag, Post, Profile,
                         instaloader, instaloadercontext, resumable_iteration)

# from my_secrets import BACKUP_USERNAME, LOGIN_CREDS, TELEGRAM_ID
from ig import (DOWNLOAD_PATH, LOGIN_CREDS, SESSION_FILE, TELEGRAM_ID,
                USERNAME, dump_to_file, get_time, instaloader_init,
                load_from_file, remove_file, telegram_send)

# from re import findall
# from requests import Timeout
# from selenium import webdriver
# from selenium.webdriver import ActionChains
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
# from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait


logger = logging.getLogger(__name__)
logFormatter = logging.Formatter(
    "[%(asctime)s] %(name)s - %(levelname)s - %(message)s")
logFormatter.datefmt = "%H:%M:%S"
# logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# console log stream hanlder
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
consoleHandler.setLevel(logging.INFO)
logger.addHandler(consoleHandler)

# DOWNLOAD_PATH = f"./temp/{HASHTAG}"
TEMP_SHORTCODES = "./temp/_shortcodes.pickle"
TEMP_POSTERS = "./temp/__posters.pickle"


def timer(func):
    """Print the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = perf_counter()  # 1
        value = func(*args, **kwargs)
        end_time = perf_counter()  # 2
        run_time = end_time - start_time  # 3
        print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value

    return wrapper_timer


@timer
def get_posters_from_shortcodes(hashtag: str, loader: instaloadercontext) -> list:
    shortcodes = {}
    posters = []

    limited_accounts = [USERNAME]

    if "#" in hashtag:
        hashtag = hashtag.replace("#", "")

    logger.info(f"Finding posts with hashtag '{hashtag}'")

    if exists(TEMP_SHORTCODES) and exists(TEMP_POSTERS):
        posters = load_from_file(TEMP_POSTERS)
        shortcodes = load_from_file(TEMP_SHORTCODES)
        logger.info(f"Found temp files. Resuming...\
            posts found so far: {len(posters)}")

    else:
        # post_iterator = instaloader.Hashtag.from_name(loader.context, hashtag).get_posts()
        post_iterator = NodeIterator(
            loader.context, "9b498c08113f1e09617a1703c22b2f32",
            lambda d: d['data']['hashtag']['edge_hashtag_to_media'],
            lambda n: instaloader.Post(loader.context, n),
            {'tag_name': hashtag},
            f"https://www.instagram.com/explore/tags/{hashtag}/"
        )

        for post in post_iterator:
            loader.download_post(post, target=hashtag)

        jsons = os.listdir(DOWNLOAD_PATH)
        for json_file in jsons:
            with open(f"{DOWNLOAD_PATH}/{json_file}", "r") as rf:
                post = json.load(rf)
                shortcode = post["node"]["shortcode"]
                shortcodes.setdefault(shortcode, False)

    not_visited = [x for x, visited in shortcodes.items() if not visited]
    logger.info(
        f"'{len(shortcodes)}' posts. not visited = {len(not_visited)}.")

    for shortcode, visited in shortcodes.items():
        if not visited:
            try:
                post = Post.from_shortcode(loader.context, shortcode=shortcode)
                sleep(round(random.uniform(1.000, 2.100), 3))
                posters.append(post.owner_username)
                print(f"{post.owner_username:<30}UTC {post.date}")
                shortcodes[shortcode] = True
                if len(posters) % 50 == 0:
                    print(f"{get_time():>50}\tposts found so far: {len(posters)}")

            # except instaloader.QueryReturnedBadRequestException as e:
            #     remove_file(SESSION_FILE)
            #     dump_to_file(shortcodes, TEMP_SHORTCODES)
            #     dump_to_file(posters, TEMP_POSTERS)
            #     logger.error(
            #         f"Bad Request Exception. Probably the account '{USERNAME}' was limited by instagram.\n\
            # To solve this: First try to *(solve captcha)* from instagram web and *(verify phone number)* and change password
            # if required.\n")
            #     telegram_send(TELEGRAM_ID, "Account limited",
            # f"Account {USERNAME} was limited, solve captcha and when it was no longer limited, press enter")
            except KeyError:
                logger.info(f"KeyError, Post {shortcode} not found.")
            except Exception as e:
                remove_file(SESSION_FILE)
                dump_to_file(shortcodes, TEMP_SHORTCODES)
                dump_to_file(posters, TEMP_POSTERS)

                logger.error(f"Exception while fetching posters! Details: {e}")
                logger.info(
                    "Saved posters and shortcodes. Trying to switch account...")

                for uname in LOGIN_CREDS.keys():
                    if uname not in limited_accounts:
                        limited_accounts.append(uname)
                        logger.info(
                            f"Switched to account {uname}. Go to login activity and 'click This Was Me'")
                        loader = instaloader_init(
                            ig_user=uname, ig_passwd=LOGIN_CREDS[uname])
                        break

                else:
                    logger.info(
                        "All accounts were limited. 1. solve the captcha 2. change password if needed. Then press ENTER to login interactively")
                    uname = input("enter instagram username: ")
                    loader = instaloader.Instaloader(filename_pattern="{date_utc:%Y-%m-%d_%H-%M-%S}-{shortcode}",
                                                     sleep=True,
                                                     download_pictures=False, post_metadata_txt_pattern="",
                                                     compress_json=False, download_geotags=False,
                                                     save_metadata=True, download_comments=False, download_videos=False,
                                                     download_video_thumbnails=False)
                    loader.interactive_login(uname)

            except KeyboardInterrupt:
                dump_to_file(shortcodes, TEMP_SHORTCODES)
                dump_to_file(posters, TEMP_POSTERS)
                logger.error("keyboardInterrupt. Saved posters and shortcodes")
                sys.exit("Exited 1")

    # Double check shortcodes and remove temporary files if all shortcodes are visited
    for shortcode, visited in shortcodes.items():
        if not visited:
            print(f"shortcode '{shortcode}' is not visited yet.")

    remove_file(TEMP_POSTERS)
    remove_file(TEMP_SHORTCODES)
    shutil.rmtree(DOWNLOAD_PATH)

    return posters


def get_hashtag_posters(hashtag, loader):
    """Find posts from hashtag"""
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
            sleep(round(random.uniform(5.000, 8.000), 3))
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
                          f"Account {USERNAME} was limited. Solve captcha and click 'This was Me', then press enter")

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

# def firefox_builder():
#     # binary = FirefoxBinary(FIREFOX_BINARY_PATH)
#     profile = FirefoxProfile(FIREFOX_PROFILE_PATH)

#     # apply the setting under (A) to ALL new windows (even script windows with features)
#     profile.set_preference("browser.link.open_newwindow.restriction", 0)
#     # open external links in a new window
#     profile.set_preference("browser.link.open_newwindow.override.external", 2)
#     # divert new window to a new tab
#     profile.set_preference("browser.link.open_newwindow", 3)
#     ##
#     profile.set_preference("network.http.connection-timeout", 5)
#     profile.set_preference("network.http.response.timeout", 5)
#     profile.set_preference("dom.max_script_run_time", 5)
#     # profile.set_preference("network.http.connection-retry-timeout", 15)
#     ##
#     # profile.update_preferences()
#     opts = webdriver.firefox.options.Options()
#     opts.headless = HEADLESS

#     # browser = webdriver.Firefox(firefox_binary=binary, options=opts, firefox_profile=profile, executable_path=FIREFOX_DRIVER_PATH)
#     browser = webdriver.Firefox(
#         options=opts, firefox_profile=profile, executable_path=FIREFOX_DRIVER_PATH)
#     browser.set_window_size(700, 700)
#     browser.get("about:config")

#     return browser


# def sleep_with_print(seconds):
#     for _ in range(seconds, 0, -1):
#         print(f"{_} \r", end="")
#         sleep(1)
#     print("          ")


# def get_hashtag_posters2(hashtag):
#     """Find hashtag posters using webdriver from https://picuki.com"""
#     posters = []
#     links = {}
#     double_check = {}

#     if hashtag[0] == "#":
#         hashtag = hashtag.replace("#", "")

#     # if temp files existed, load and skip loading from websites
#     if os.path.exists(POSTERS_TEMP_FILE) and os.path.exists(LINKS_TEMP_FILE):
#         posters = load_from_file(POSTERS_TEMP_FILE)
#         links = load_from_file(LINKS_TEMP_FILE)
#         logger.info("Loaded links from file.")

#     # if temp files didn't exist, load from website
#     else:
#         browser = firefox_builder()
#         logger.info("Connect your VPN")
#         sleep_with_print(10)
#         # preventing browser.get hang
#         # browser.set_script_timeout(0)
#         # browser.set_page_load_timeout(5)

#         logger.info(
#             f"Finding posts with hashtag '{hashtag}'. This will take some time")
#         reload = True
#         while reload:
#             try:
#                 browser.get(f"https://www.picuki.com/tag/{hashtag}")
#                 # browser.get(f"https://gramho.com/explore-hashtag/{hashtag}")
#                 reload = False

#                 assert "Instagram" in browser.title, "Could not load main page properly. Make sure VPN is connected"
#             except selenium.common.exceptions.WebDriverException as e:
#                 if "Failed to decode response from marionette" in e.msg:
#                     logger.exception(
#                         "Something's wrong with browser, Is it even open?")
#                     sys.exit(1)
#                 else:
#                     logger.error(
#                         "Could not load posts page. Make sure VPN is connected. Retrying in...")
#                     sleep_with_print(4)
#             except Exception as e:
#                 logger.error(
#                     "Could not load posts page. Make sure VPN is connected. Retrying...")
#         # find total number of posts
#         total_post_element = browser.find_element_by_css_selector(
#             "html body div.wrapper div.content div.content-header.tag-page.clearfix div.content-title div.content-subtitle")
#         total_posts = int(total_post_element.text.split(" ")[0])
#         logger.info(f"Total posts in theory = {total_posts}")

#         # Scroll down to load all the posts
#         body_element = browser.find_element_by_tag_name('body')
#         for _ in range(1, int(total_posts / 10)+1):
#             print(
#                 f"Loading more posts. Attempt {_}/{int(total_posts / 10)}\r", end="")
#             browser.execute_script(
#                 "window.scrollTo(0, document.body.scrollHeight);")
#             sleep(1)
#             for _ in range(0, 15):
#                 body_element.send_keys(Keys.ARROW_UP)
#             sleep(3)
#             # body_element.send_keys(Keys.END)
#             # sleep(5)
#             # body_element.send_keys(Keys.END)
#             # body_element.send_keys(Keys.ARROW_UP)
#             # body_element.send_keys(Keys.HOME)
#             # sleep(0.3)
#         # save post link to `links`
#         posts_elements = browser.find_elements_by_css_selector(
#             "html body div.wrapper div.content.box-photos-wrapper ul.box-photos.clearfix li div.box-photo div.photo a")
#         for post in posts_elements:
#             link = post.get_attribute("href")
#             # visit status, True: link already visited - False: link not visited
#             links.setdefault(link, False)

#         # Save loaded posts to file
#         dump_to_file(links, LINKS_TEMP_FILE)
#         dump_to_file(posters, POSTERS_TEMP_FILE)
#         browser.quit()

#     logger.info(f"Total posts found in action: '{len(links)}'")
#     while False in links.values():  # while there is a link that is not visited:
#         with requests.session() as session:  # open a requests.session
#             for link, visited in links.items():
#                 if not visited:
#                     try:
#                         # response = requests.get(link, timeout=5)
#                         response = session.get(link, timeout=5)  # get the link
#                         if response.status_code == 404:
#                             double_check.setdefault(link, 0)
#                             double_check[link] += 1
#                             logger.error(
#                                 f"Post not found '{link}', double_check status: {double_check[link]}/3")
#                             if double_check[link] == 3:
#                                 logger.info(
#                                     f"Marking link '{link}' as visited after three 404 responses.")
#                                 links[link] = True
#                         elif response.status_code == 403:
#                             logger.error(
#                                 "Forbidden 403, try changing your vpn, resting for 1 minute... (Disconnect/Connect your vpn dude)")
#                             sleep_with_print(30)
#                         elif response.status_code == 200:  # if the status code was 200, grab the username
#                             username = findall(
#                                 "@[a-zA-Z0-9_.]*", response.text)
#                             # username without the beginning @
#                             posters.append(username[0][1:])
#                             print(username[0])
#                             links[link] = True
#                     except KeyboardInterrupt:
#                         dump_to_file(links, LINKS_TEMP_FILE)
#                         dump_to_file(posters, POSTERS_TEMP_FILE)
#                         logger.info("Keyboard Interrupt!")
#                         sys.exit(1)
#                     except (ConnectionError, Timeout):
#                         logger.error(
#                             "Connection Timeout or Error, Check VPN. Retrying in...")
#                         sleep_with_print(5)
#                     except Exception as e:
#                         dump_to_file(links, LINKS_TEMP_FILE)
#                         dump_to_file(posters, POSTERS_TEMP_FILE)

#                     # Rest
#                     if posters and len(posters) % 50 == 0:
#                         print(
#                             f"\t\t\t{get_time()}\tPosts so far: {len(posters)}, Resting 1 minute...")
#                     #     sleep_with_print(60)
#                     # elif posters and len(posters) % 20 == 0:
#                     #     print("\t\t\tResting for 1/2 minute...")
#                     #     sleep_with_print(30)

#     # Double check links and remove temporary files if all links are visited
#     for link, visited in links.items():
#         if not visited:
#             logger.info(f"link '{link}' is not visited yet.")
#     if not (False in links.values()):
#         remove_file(POSTERS_TEMP_FILE)
#         remove_file(LINKS_TEMP_FILE)

#     return posters


# def get_hashtag_posters3(hashtag):
#     posters = []
#     links = {}
#     total_posts = 600

#     if "#" in hashtag:
#         hashtag = hashtag.replace("#", "")

#     browser = firefox_builder()
#     logger.info("Connect your VPN")
#     sleep_with_print(10)

#     logger.info(
#         f"Finding posts with hashtag '{hashtag}'. This will take some time")
#     reload = True
#     while reload:
#         try:
#             # find total number of posts
#             browser.get(f"https://www.picuki.com/tag/{hashtag}")
#             total_post_element = browser.find_element_by_css_selector(
#                 "html body div.wrapper div.content div.content-header.tag-page.clearfix div.content-title div.content-subtitle")
#             total_posts = int(total_post_element.text.split(" ")[0])
#             logger.info(f"Total posts in theory = {total_posts}")

#             browser.get(f"https://www.stalkhub.com/tag/{hashtag}/")
#             reload = False

#             assert "Instagram" in browser.title, "Could not load main page properly. Make sure VPN is connected"
#         except selenium.common.exceptions.WebDriverException as e:
#             if "Failed to decode response from marionette" in e.msg:
#                 logger.exception(
#                     "Something's wrong with browser, Is it even open?")
#                 sys.exit(1)
#             else:
#                 logger.error(
#                     "Could not load posts page. Make sure VPN is connected. Retrying in...")
#                 sleep_with_print(4)
#         except Exception as e:
#             logger.error(
#                 "Could not load posts page. Make sure VPN is connected. Retrying...")

#     browser.find_element_by_css_selector(
#         ".search-area > form:nth-child(1) > input:nth-child(1)").send_keys(hashtag)
#     browser.find_element_by_partial_link_text("Tags").click()
#     browser.find_element_by_partial_link_text(hashtag).click()

#     # top_posts = browser.find_element_by_css_selector(
#     #     "html.wf-roboto-n4-active.wf-roboto-n5-active.wf-roboto-n7-active.wf-roboto-n9-active.wf-active body div.general-card-list.hastag-ranked-card-list div.container")
#     # top_posters = top_posts.find_elements_by_class_name("user-name")

#     # Scroll down to load all the posts
#     for _ in range(1, int(total_posts / 10)+1):
#         print(
#             f"Loading more posts. Attempt {_}/{int(total_posts / 10)}\r", end="")
#         height = browser.execute_script("return document.body.scrollHeight")
#         scroll_position = browser.execute_script("return window.scrollY")

#         while scroll_position < height - 1500:
#             browser.execute_script("window.scrollBy(0,700)")
#             sleep(round(uniform(1.000, 1.500), 3))
#             scroll_position = browser.execute_script("return window.scrollY")

#         load_more_btn = browser.find_element_by_css_selector(
#             "html.wf-roboto-n4-active.wf-roboto-n5-active.wf-roboto-n7-active.wf-roboto-n9-active.wf-active body div#getRecentData.general-card-list.load-more-area div.container div.button-area button#loadMoreButton.next-button")

#         ActionChains(browser).move_to_element(load_more_btn).click().perform()
#         sleep(4)

#     posts_elements = browser.find_elements_by_css_selector(
#         "html body div.wrapper div.content.box-photos-wrapper ul.box-photos.clearfix li div.box-photo div.photo a")
#     for post in posts_elements:
#         link = post.get_attribute("href")
#         # visit status, True: link already visited - False: link not visited
#         links.setdefault(link, False)

#     browser.quit()

#     return posters


# def get_tagged_posters(username, loader):
#     """Find posters that tagged a username"""
#     ITTERATOR_TEMP = "temp/frozenNodeIterator.pickle.tmp"
#     POSTERS_TEMP = "temp/posters.pickle.tmp"
#     posters = []

#     logger.info(
#         f"Finding posts that user '{username}' was tagged in. This will take some time to complete! (25-35 minutes for every ~500 posts)")

#     profile = Profile.from_username(loader.context, username)
#     post_iterator = profile.get_tagged_posts()

#     if exists(ITTERATOR_TEMP):
#         loded_itr = load_from_file(ITTERATOR_TEMP)
#         posters = load_from_file(POSTERS_TEMP)
#         logger.info(
#             f"Loaded post-itterator and {len(posters)} posts from file, continuing...")
#         post_iterator.thaw(loded_itr)

#     print("TYPE: ", type(post_iterator.freeze()))
#     try:
#         for post in post_iterator:
#             sleep(round(uniform(1.000, 3.000), 3))
#             posters.append(post.owner_username)
#             print(post.owner_username, "\t", post.date)
#             if len(posters) % 50 == 0:
#                 print(
#                     f"\t\t\t{get_time()}\tposts found so far: {len(posters)}")
#     except KeyboardInterrupt as e:
#         dump_to_file(post_iterator.freeze(), ITTERATOR_TEMP)
#         dump_to_file(posters, POSTERS_TEMP)

#         logger.error(
#             f"keyboardInterrupt, dummped posters found so far to file. EXITED\n Details: {e}")
#         sys.exit("User interrupted execution.\n EXITED 1")
#     except instaloader.QueryReturnedBadRequestException as e:
#         dump_to_file(post_iterator.freeze(), ITTERATOR_TEMP)
#         dump_to_file(posters, POSTERS_TEMP)
#         remove_file(SESSION_FILE)

#         logger.exception(f"Exception details:\n {e}")
#         logger.error(
#             f"Bad Request Exception. Probably the account '{USERNAME}' was limited by instagram.\n\
#                 To solve this: First try to *(solve captcha)* from instagram web and *(verify phone number)* and change password if required.\n\
#                 You can also change -u command line argument to another account to fix this error")
#         sys.exit("\nEXITED 1")

#     except Exception as e:
#         dump_to_file(post_iterator.freeze(), ITTERATOR_TEMP)
#         dump_to_file(posters, POSTERS_TEMP)

#         logger.error(
#             f"Exception in fetching posts from instagram, EXITED\n Details: {e}")
#         sys.exit(
#             "Probably your internet was disconnected, 'Try to run again!!' \nEXITED 1")

#     remove_file(ITTERATOR_TEMP)
#     remove_file(POSTERS_TEMP)
#     return posters
