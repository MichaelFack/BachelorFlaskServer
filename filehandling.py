import json
import os
import string
import threading
import time

from werkzeug.utils import secure_filename

import app

LIVE_FILES_LOG_LOCK = threading.Lock()
ADDITIONAL_DATA_LOG_LOCK = threading.Lock()


def list_live_files():  # In Admin there exists a file dict
    LIVE_FILES_LOG_LOCK.acquire()
    # Does the log exist?
    if not os.path.isfile(app.LIVE_FILES_LOG):
        LIVE_FILES_LOG_LOCK.release()
        return []
    with open(app.LIVE_FILES_LOG, 'r') as live_files_log_file:
        data = json.load(live_files_log_file)
    LIVE_FILES_LOG_LOCK.release()
    # Obtain the set of names 'live'.
    live_files = []
    for name, isLive in data.items():
        if isLive: live_files.append([name, load_additional_data(latest_filename_version(name))['nonce1']])
    return live_files


def set_file_liveness(filename, set_to):
    LIVE_FILES_LOG_LOCK.acquire()
    # Does the log exist?
    if not os.path.isfile(app.LIVE_FILES_LOG):
        LIVE_FILES_LOG_LOCK.release()
        return False
    with open(app.LIVE_FILES_LOG, 'r') as live_files_log_file:
        data = json.load(live_files_log_file)
    # Does the log contain the name?
    if filename not in data.keys():
        LIVE_FILES_LOG_LOCK.release()
        return False
    # Is it not 'set_to'?
    if set_to == data[filename]:
        LIVE_FILES_LOG_LOCK.release()
        return False
    # If so; set it to 'set_to'.
    data[filename] = set_to
    with open(app.LIVE_FILES_LOG, 'w') as live_files_log_file:
        json.dump(data, live_files_log_file)
    LIVE_FILES_LOG_LOCK.release()
    return True


def archive_file(filename):
    return set_file_liveness(filename, False)


def resurrect_file(filename):
    return set_file_liveness(filename, True)


def mark_file_as_live(filename):
    LIVE_FILES_LOG_LOCK.acquire()
    # Does the log exist?
    if not os.path.isfile(app.LIVE_FILES_LOG):
        with open(app.LIVE_FILES_LOG, 'w') as live_log:
            json.dump({filename: True}, live_log)  # First entry.
        LIVE_FILES_LOG_LOCK.release()
        return
    with open(app.LIVE_FILES_LOG, 'r') as live_log:
        data = json.load(live_log)
    data[filename] = True
    with open(app.LIVE_FILES_LOG, 'w') as live_log:
        json.dump(data, live_log)
    LIVE_FILES_LOG_LOCK.release()


def save_file_and_additional_data(file, avail_filename, additional_data):  # TODO: How to test this?
    file.save(os.path.join(app.UPLOAD_FOLDER, avail_filename))
    store_additional_data(avail_filename, additional_data)


def store_additional_data(server_side_name, additional_data):
    ADDITIONAL_DATA_LOG_LOCK.acquire()
    if not os.path.isfile(app.ADDITIONAL_DATA_LOG):
        # If the file doesn't already exist, just dump a simple map into it.
        with open(app.ADDITIONAL_DATA_LOG, 'w') as add_log:
            json.dump({server_side_name: additional_data}, add_log)
        ADDITIONAL_DATA_LOG_LOCK.release()
        return
    with open(app.ADDITIONAL_DATA_LOG, 'r') as add_log:
        data = json.load(add_log)
    data[server_side_name] = additional_data
    with open(app.ADDITIONAL_DATA_LOG, 'w') as add_log:
        json.dump(data, add_log)
    ADDITIONAL_DATA_LOG_LOCK.release()


def load_file_path_and_additional_data(server_side_name):
    filepath = os.path.join(app.UPLOAD_FOLDER, server_side_name)
    if not os.path.isfile(filepath):
        return None, None
    additional_data = load_additional_data(server_side_name)
    if additional_data is None:
        return None, None
    return filepath, additional_data


def load_additional_data(filename):
    ADDITIONAL_DATA_LOG_LOCK.acquire()
    # Does the log exist?
    if not os.path.isfile(app.ADDITIONAL_DATA_LOG):
        ADDITIONAL_DATA_LOG_LOCK.release()
        return None
    with open(app.ADDITIONAL_DATA_LOG, 'r') as add_log:
        data = json.load(add_log)
    ADDITIONAL_DATA_LOG_LOCK.release()
    # Does the log contain an entry for our filename?
    if filename not in data.keys():
        return None
    return data[filename]


def load_latest_timestamp(filename):
    latest_filename = latest_filename_version(filename)
    additional_data_of_file = load_additional_data(latest_filename)  # A bit redundant.
    if additional_data_of_file is None:
        return None
    return additional_data_of_file['t']


def get_available_name(filename, timestamp):
    for i in range(100):
        avail_filename = filename_to_server_side_name(filename, timestamp, i)
        if not os.path.isfile(avail_filename):
            break
    if os.path.isfile(avail_filename):
        return None
    return avail_filename


def matching_additional_data(filename, additional_data):
    # For the additional data to match the name has to match
    # and the time cannot be in the future or older than 60 secs.
    if additional_data['n'] == filename:
        return True
    else:
        app.write_to_error_log("Names doens't match: " + filename + "!=" + additional_data['n'])
        return False


def acceptable_filename(filename):
    if '.' not in filename: return False
    filename_fragments = filename.rsplit('.', 1)
    if filename_fragments[1].lower() not in app.ALLOWED_EXTENSIONS: return False
    for char in filename_fragments[0]:
        if char not in string.hexdigits:
            return False
    return True


def filename_to_server_side_name(filename, timestamp, index):
    # Lets be defensive and assert that the name is safe:
    if not acceptable_filename(filename):
        raise Exception("Server was asked to translate unsafe filename; won't do that.")
    filename_fragments = filename.split('.', 1)  # [filename, ext]
    server_side_name = filename_fragments[0] + '_' + str(timestamp) + '_' + str(index) + '.' + filename_fragments[1]
    return server_side_name


def server_side_name_to_filename(server_side_name):
    filename = server_side_name.rsplit('_')[0]
    file_ext = server_side_name.rsplit('.')[-1]
    return filename + '.' + file_ext


def latest_filename_version(filename):
    files = os.listdir(app.UPLOAD_FOLDER)
    filename_prefix = filename.split('.')[0]  # name part of request
    curr_timestamp = 0.0  # 1970, 1st of january, 0:00
    curr_latest_filename = None
    for filename_in_list in files:
        if filename_prefix == filename_in_list.rsplit('_', 2)[0]:  # name == name
            file_timestamp = float(filename_in_list.rsplit('_', 2)[1])
            if curr_latest_filename is None or curr_timestamp < file_timestamp:
                curr_latest_filename = filename_in_list
                curr_timestamp = file_timestamp
    return curr_latest_filename
