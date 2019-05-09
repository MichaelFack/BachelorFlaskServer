import json
import os
import string
import threading

import app
import filehandling
from pathing import UPLOAD_FOLDER, ADMIN_FOLDER, ADDITIONAL_DATA_LOG_FILENAME, LIVE_FILES_LOG_FILENAME, USER_CATALOG
LIVE_FILES_LOG_LOCKS = {}
ADDITIONAL_DATA_LOG_LOCKS = {}


class UserMethodPack:
    def __init__(self, user_identification_string: str):
        self.userID = user_identification_string

    def upload_directory(self): return os.path.join(UPLOAD_FOLDER, "USER" + self.userID)

    def admin_directory(self): return os.path.join(ADMIN_FOLDER, "USER" + self.userID)

    def add_data_log_path(self):
        return os.path.join(self.admin_directory(), ADDITIONAL_DATA_LOG_FILENAME)

    def live_files_log_path(self):
        return os.path.join(self.admin_directory(), LIVE_FILES_LOG_FILENAME)

    def exists(self):
        if not all(s in string.hexdigits for s in self.userID):
            app.write_to_error_log("UserID not in hexdigits.")
            return False
        if not os.path.isdir(app.ADMIN_FOLDER):
            return False
        if not os.path.isfile(USER_CATALOG):
            return False
        with open(USER_CATALOG, 'r') as catalog:
            users = json.load(catalog)
        return self.userID in users

    def register(self):
        if not all(s in string.hexdigits for s in self.userID):
            app.write_to_error_log("UserID not in hexdigits.")
            return False
        if not os.path.isdir(app.ADMIN_FOLDER):
            os.mkdir(app.ADMIN_FOLDER)
        if not os.path.isfile(USER_CATALOG):
            with open(USER_CATALOG, 'w') as catalog:
                json.dump({self.userID: self.userID}, catalog)
        else:
            with open(USER_CATALOG, 'r') as catalog:
                users = json.load(catalog)
            users[self.userID] = self.userID
            with open(USER_CATALOG, 'w') as catalog:
                json.dump(users, catalog)

    def unregister(self):  # Maybe delete content of user when unregistered?
        if not all(s in string.hexdigits for s in self.userID):
            app.write_to_error_log("UserID not in hexdigits.")
            return False
        if not os.path.isdir(app.ADMIN_FOLDER):
            return False
        if not os.path.isfile(USER_CATALOG):
            return False
        else:
            live_files = filehandling.list_live_files(self)  # archive live files
            for file, nonce, ts in live_files:
                filehandling.archive_file(file, self)
            with open(USER_CATALOG, 'r') as catalog:
                users: dict = json.load(catalog)
            keysToPop = []
            for key in users.keys():  # For each key make sure it doesn't point at the user we're deleting, ...
                if users[key] == self.userID or users[key] not in users.keys():  # ... or at something not contained...
                    keysToPop.append(key)  # ... as these are all aliases of our user.
            for key in keysToPop:
                users.pop(key)
            with open(USER_CATALOG, 'w') as catalog:
                json.dump(users, catalog)

    def acquire_live_files_log_lock(self):
        if self.userID in LIVE_FILES_LOG_LOCKS.keys():
            lock: threading.Lock = LIVE_FILES_LOG_LOCKS[self.userID]
            lock.acquire()
        else:
            lock = threading.Lock()
            lock.acquire()
            LIVE_FILES_LOG_LOCKS[self.userID] = lock

    def release_live_files_log_lock(self):
        lock: threading.Lock = LIVE_FILES_LOG_LOCKS[self.userID]
        lock.release()

    def acquire_additional_data_log_lock(self):
        if self.userID in ADDITIONAL_DATA_LOG_LOCKS.keys():
            lock: threading.Lock = ADDITIONAL_DATA_LOG_LOCKS[self.userID]
            lock.acquire()
        else:
            lock = threading.Lock()
            lock.acquire()
            ADDITIONAL_DATA_LOG_LOCKS[self.userID] = lock

    def release_additional_data_log_lock(self):
        lock: threading.Lock = ADDITIONAL_DATA_LOG_LOCKS[self.userID]
        lock.release()

