import json
import os
import secrets
import time
from threading import Lock
from hashlib import sha3_512

import app

challenge_log_lock = Lock()


def issue_challenge(user_id):
    challenge = secrets.token_hex(app.LOGIN_CHALLENGE_LENGTH)
    if user_exists(user_id):
        log_latest_challenge(user_id, challenge)
    return challenge


def user_exists(USER_IDENTIFIER):
    for user in get_users():  # Should be fine as long as |users| < a lot
        if user[0] == USER_IDENTIFIER:
            return True
    return False


def get_users():
    if not os.path.isfile(app.USER_CATALOG):
        return []
    with open(app.USER_CATALOG, 'r') as file:
        return json.load(file)


def log_latest_challenge(USER_IDENTIFIER, challenge):
    challenge_log_lock.acquire()
    challenge_log_path = os.path.join(app.ADMIN_FOLDER, 'live_challenges')
    if os.path.isfile(challenge_log_path):
        with open(challenge_log_path, 'r') as log:
            challenge_dict = json.load(log)
    else:
        challenge_dict = {}
    challenge_dict[USER_IDENTIFIER] = {'c': challenge, 't': time.time()}  # 1 live per user - is fine if |users| < a lot
    with open(challenge_log_path, 'w') as log:
        json.dump(challenge_dict, log)
    challenge_log_lock.release()


def get_latest_challenge(USER_IDENTIFIER):
    challenge_log_lock.acquire()
    challenge_log_path = os.path.join(app.ADMIN_FOLDER, 'live_challenges')
    latest_challenge = None
    if os.path.isfile(challenge_log_path):
        with open(challenge_log_path, 'r') as log:
            challenge_dict = json.load(log)
        if USER_IDENTIFIER in challenge_dict.keys():
            challenge = challenge_dict[USER_IDENTIFIER]
            curr_time = time.time()
            if curr_time - challenge['t'] > 60 or curr_time - challenge['t'] < 0:
                latest_challenge = None  # If the latest challenge is outdated or in the future;
            else:
                latest_challenge = challenge['c']
    challenge_log_lock.release()
    return latest_challenge


def validate_challenge_response(user_id, challenge_response):
    latest_challenge = get_latest_challenge(user_id)
    if latest_challenge is None: return False
    correct_challenge_response = compute_challenge_response(latest_challenge, user_id)
    return challenge_response == correct_challenge_response


def get_user_salt(user_id):  # TODO: Might need another impl.
    users = get_users()
    for user_id_, salt in users:
        if user_id_ == user_id:
            return salt
    return None


def compute_challenge_response(latest_challenge, user_id):
    hash_func = sha3_512()
    salt = get_user_salt(user_id)
    if salt is None: return None
    hash_func.update(bytearray.fromhex(salt))
    hash_func.update(bytearray.fromhex(latest_challenge))
    hash_func.update(b'latest_challenge')
    return hash_func.hexdigest()


def create_user(USER_IDENTIFIER, HASH_IDENTIFIER):
    if not os.path.isfile(app.USER_CATALOG):
        with open(app.USER_CATALOG, 'w+') as file:
            json.dump([(USER_IDENTIFIER, HASH_IDENTIFIER)], file)
    else:
        with open(app.USER_CATALOG, 'r') as file:
            users = json.load(file)  # List?
        if USER_IDENTIFIER in map(lambda x: x[0], users):
            return False
        users.append((USER_IDENTIFIER, HASH_IDENTIFIER))
        with open(app.USER_CATALOG, 'w') as file:
            json.dump(users, file)
    return True
