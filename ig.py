#!/usr/bin/env python3

# aajeZzZzZzzzPlus
# This script finds clients that didn't like top3 posts.
# --------------------------------------------------------------------------
# import json
import logging
import os
import pickle
import random
import sys
import time
from argparse import ArgumentParser
from datetime import datetime, timedelta
# from json import dump, load
from os.path import exists

# import jdatetime
import pysftp
# import requests
# import selenium
# from bullet import Bullet, Check, Input, YesNo  # and etc...
from instaloader import Post, Profile, instaloader
from pyrogram import Client

import getposters

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
ADMINS = ["Improve_2020", "Girlylife.mm", "ghazal.nasiriyan"]

VIPS = ["solace.land"]

# HASHTAG = "TAG--" + jdatetime.datetime.now().strftime("%A-%d-%m-%Y--%H-%M")
HASHTAG = ""
TAGGED_PROFILE = "pishraftmikonim"
TOP3 = ['', '', '']
# --------------------------------------------------------------------------
# Constants (Variables you can't change unless you know what you are doing)
# PASSWORD = LOGIN_CREDS[USERNAME.lower()]
SESSION_FILE = f"sessions/{USERNAME}-SESSION"
WARN_HISTORY_REMOTE_PATH = "/littleuzer/ig/warn_history.pickle"
WARN_HISTORY_FILE = "data/warn_history.pickle"
LAST_WARN_LIST = "data/last_warning_list"
CLIENTS_LIST = "data/clients_list"
VIP_CLIENTS_LIST = "data/VIP_clients_list"
LAST_HASHTAG_STR = "data/last_hashtag_str"
DOWNLOAD_PATH = f"temp/DOWNLOADED"
TEMP_HASHTAG = "temp/hashtag.str"
TEMP_TOP3 = "temp/top3.list"
TEMP_SHORTCODES = "temp/_shortcodes.pickle"
TEMP_POSTERS = "temp/posters.pickle"
LINKS_TEMP_FILE = "temp/_links.pickle"
POSTERS_TEMP_FILE = "./temp/_posters.pickle"
COMPLETE_EXECUTION = False
PWD = os.getcwd()
FIREFOX_DRIVER_PATH = rf"{PWD}/drivers/geckodriver"
FIREFOX_PROFILE_PATH = r"/home/user/.mozilla/firefox/euvy32zo.freshprofile"
HEADLESS = False
# --------------------------------------------------------------------------

logger = logging.getLogger()


def get_time():
    return datetime.now().strftime("%d-%m-%Y--%H-%M")


def setup_logging():

    # disable loggin of pyrogram except for errors
    logging.getLogger('pyrogram').setLevel(logging.ERROR)
    # logging.getLogger('foo').addHandler(logging.NullHandler()) # Disables logging of the module

    global logger
    now = get_time()

    logFormatter = logging.Formatter(
        "[%(asctime)s] %(name)s - %(levelname)s - %(message)s")
    logFormatter.datefmt = "%H:%M:%S"
    logger = logging.getLogger(__name__)
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
    "Parse message and split it to chunks then send the message to the @user_id"
    hashtag = HASHTAG
    if "#" not in hashtag:
        hashtag = "#" + hashtag

    if isinstance(message, str):
        message = message.splitlines()

    split = [f"#{header} <b>{hashtag}</b> 👇🏼"]
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
    with Client("sessions/pyrog.session", APP_ID, API_HASH) as app:
        # messages = app.get_history(-1001300601863)
        # gif = choice(messages)
        # app.forward_messages(chat_id=user_id, from_chat_id=-1001300601863, message_ids=gif.message_id, as_copy=True)
        for _ in range(0, 10):
            try:
                gif_id = random.choice(
                    range(2, app.get_history_count(chat_id=-1001300601863)))
                app.forward_messages(
                    chat_id=user_id, from_chat_id=-1001300601863, message_ids=gif_id, as_copy=False)
                break
            except Exception:
                pass


def telegram_send_document(user_id, doc):
    with Client("sessions/pyrog.session", APP_ID, API_HASH) as app:
        app.send_document(user_id, document=doc)


def instaloader_init(ig_user=USERNAME, ig_passwd=PASSWORD):
    global SESSION_FILE
    SESSION_FILE = f"sessions/{ig_user}-SESSION"

    # Get instance
    L = instaloader.Instaloader(dirname_pattern=DOWNLOAD_PATH, filename_pattern="{date_utc:%Y-%m-%d_%H-%M-%S}-{shortcode}", sleep=True,
                                download_pictures=False, post_metadata_txt_pattern="", compress_json=False, download_geotags=False,
                                save_metadata=True, download_comments=False, download_videos=False, download_video_thumbnails=False)

    if not exists(SESSION_FILE):
        logger.info(f"Logging-in with account '{ig_user}'...")
        L.login(ig_user, ig_passwd)        # (login)
        L.save_session_to_file(filename=SESSION_FILE)
        # L.interactive_login(USER)      # (ask password on terminal)

    else:
        L.load_session_from_file(ig_user, SESSION_FILE)

    return L


def get_followings(usernames, loader):
    """find followings of admin users (subscribed users and VIP users)"""
    followings = []

    logger.info(f"Fetching admin:{usernames} followees...")

    try:
        for username in usernames:
            profile = Profile.from_username(loader.context, username)
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

    logger.debug(f"admin(s) {usernames} followings: {followings}")

    return list(set(followings))


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


def find_assholes(top_posts):
    """Finds clients that didn't like top posts. First loads or update clients list.
    Then finds all posts with given hashtag. Then finds top-posts likers.
    Finally finds which client didn't like top-posts at all."""

    bitches = []    # users that posted the hashtag but aren't clients
    cheaters = []   # hastag_posters with more than one post
    clients_likes = {}  # saving client like per post to find assholes
    assholes = []  # Assholes, clients that didn't like top posts

    logger.info(f"Current datetime: {get_time()}")
    logger.debug(f"Inputs: \n\tHashtag: '{HASHTAG}'\n\tAdmins: {ADMINS}\n\tVIP-Admins: {VIPS}\n\
        \tThree Posts: {top_posts}\n\tAccount: '{USERNAME}'\n\tTagged Profile: '{TAGGED_PROFILE}'")

    # fetch all clients from ADMINS's followings
    clients = load_or_update(ADMINS + VIPS, CLIENTS_LIST)
    logger.info(f"Total '{len(clients)}' subscribed clients found.")
    logger.debug(f"Clients:\n\t{sorted(clients)}\n\n")

    L = instaloader_init()

    # fetch hashtag posters from instagram or load from last unsuccessful execution
    if exists(POSTERS_TEMP_FILE+"_"):
        posters = load_from_file(POSTERS_TEMP_FILE+"_")
    else:
        posters = getposters.get_posters_from_shortcodes(HASHTAG, loader=L)
        # posters = get_hashtag_posters(HASHTAG, L)
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
            posters.remove(poster)   # remove bitches from posters
        if posters.count(poster) > 1:
            cheaters.append(poster)
            posters.remove(poster)

    # remove dulicate usernames
    posters = list(set(posters))
    logger.info(
        f"'{len(posters)}' unique posts from clients:\t{sorted(posters)}")

    # find likers of every post and mark those who didn't like them
    logger.info(f"Fetching posts {top_posts} likes from instagram...")
    for shortcode in top_posts:
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
                if clients_likes[user] == len(top_posts):
                    assholes.append(user)
        time.sleep(5)

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

    telegram_send(
        DUDE, f"total {total} | bitches {len(set(bitches))} | cheaters {len(set(cheaters))}", "")

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


def update_warndb(warned_clients, hashtag):
    """creates(if not already existed) or updates the warned users dictionary"""

    if "#" in hashtag:
        hashtag = hashtag.replace("#", "")

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
        if hashtag not in warn_dic[client] and hashtag != "":
            warn_dic[client].add(hashtag)

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


def load_or_update(client_admins, c_file) -> list:
    """loads given admin's clients list from file or updates them from instagram. Used for clients and VIP clients"""
    # TODO: add time based decision of fetching or loading from file: DONE!
    clients = []

    update = False
    string = "clients"
    if "vip" in c_file.lower():
        string = "VIP " + string

    if exists(c_file):
        hour_ago = datetime.now() - timedelta(minutes=90)
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
    
    # devide assholes by admin
    L = instaloader_init()
    assholes_per_admin = {}
    admins_followers = {}

    for admin in ADMINS:
        assholes_per_admin.setdefault(admin, "")
        followers = get_followings([admin], L)
        admins_followers[admin] = followers

    psign = "+"
    for client in sorted(last_warn_list):
        if client not in vip_clients:
            for admin, admins_clients in admins_followers.items():
                if client in admins_clients:
                    assholes_per_admin[admin] += f"{client} {psign * ((len(warn_dic[client])-1) % 3)}\n"
    
    # fancy = ""
    # psign = "+"
    # for client in sorted(last_warn_list):
    #     if client not in vip_clients:
    #         fancy = fancy + \
    #             f"{client} {psign * ((len(warn_dic[client])-1) % 3)}\n"
    #         if client in warn_dic.keys():
    #             print("+" * (len(warn_dic[client])-1), end='')
    #         print("")

    print(
        f"\nFancy little list of to-be-warned clients (assholes) for hashtag '{HASHTAG}' excluding VIPs:\n")
    print(assholes_per_admin)
    # print(fancy)

    if COMPLETE_EXECUTION:  # write fancy list to report file if find assholes function was called before
        total_assholes_count = 0
        for admin, fancy in assholes_per_admin.items():
            with open(f"logs/report-{HASHTAG}.txt", "a") as af:
                af.write(fancy)
            assholes_count = len(fancy.split('\n'))
            total_assholes_count += assholes_count
            telegram_send(TELEGRAM_ID, f"ASSHOLES '{assholes_count}', admin: {admin}", fancy)

        telegram_send_gif(TELEGRAM_ID)
        telegram_send(DUDE, f"assholes  {total_assholes_count}", "")
        telegram_send_document(DUDE, WARN_HISTORY_FILE)


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
        update_warndb(tobe_warned_manual, hashtag=HASHTAG)

    elif continuee.lower() == "2":
        print("Cool. Job canceled and didn't update. Bye.")

    # Update last warn file
    old_last_warning = load_from_file(LAST_WARN_LIST)
    new_last_warning = []
    new_last_warning.extend(old_last_warning)
    new_last_warning.extend(tobe_warned_manual)
    dump_to_file(new_last_warning, LAST_WARN_LIST)


def menu():
    global HASHTAG, COMPLETE_EXECUTION, TAGGED_PROFILE, TOP3
    while True:
        read_inputs = True
        choices = ["1> Find Assholse\t(Find clients that didn't like posts of a certain hashtag)", "2> Print Warning History\t(History of asshole clients from the beginning of the time)",
                   "3> Print Last Assholes\t(Print asshole clients (one in each line) of the last search)", "4> Manually Update Warning History (update warning history file manually from a list of input clients)",
                   "5> Exit", "6> Find Assholes with latest inputs (EXPERIMENTAL)"]

        print("Main Menu:")
        for option in choices:
            print(f"  {option}")
        user_choice = input("Enter number of the job you want to do: ")

        if user_choice == "6":
            if exists(TEMP_HASHTAG) and exists(TEMP_TOP3):
                HASHTAG = load_from_file(TEMP_HASHTAG)
                TOP3 = load_from_file(TEMP_TOP3)
                user_choice = "1"
                read_inputs = False
            else:
                print("Could not find lastest execution info!!!\n")
                continue

        if user_choice == "1":
            if read_inputs:
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

            print(f"Current Inputs:\n\
            \tHashtag: '{HASHTAG}'\n\
            \tAdmins: {ADMINS}\n\
            \tVIP-Admins: {VIPS}\n\
            \tThree Posts: {TOP3}\n\
            \tAccount: '{USERNAME}'\n\
            \tTgged profile: '{TAGGED_PROFILE}'\n")

            continuee = input(
                "Are these inputs correct? \n\t1> yes, Proceed\n\t2> no, Exit\nYour choice: ")
            if continuee.lower() == "1" or continuee == "\n":
                # setup_logging()
                COMPLETE_EXECUTION = True
                dump_to_file(HASHTAG, TEMP_HASHTAG)
                dump_to_file(TOP3, TEMP_TOP3)

                assholes = find_assholes(top_posts=TOP3)
                update_warndb(assholes, hashtag=HASHTAG)
                print_last_warn()

                remove_file(TEMP_HASHTAG)
                remove_file(TEMP_TOP3)

            elif continuee.lower() == "2":
                print("\nSo edit the inputs and re-run the script! (To edit the Account or Admins or VIP-Admins, manually edit the source file.)")
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
                f"Your choice should be between 1-{len(choices)}! Choose wisely.")

        print("")
        for t in range(3, 0, -1):
            print(f"\rReloading main menu... {t}", end="")
            time.sleep(1.5)
        print("\n"*4)


if __name__ == "__main__":
    setup_logging()
    menu()

    # with open(WARN_HISTORY_FILE, 'rb') as dbfile:
    #     warn_dic = pickle.load(dbfile)
    # for client in sorted(warn_dic):
    #         print(client, warn_dic[client])
