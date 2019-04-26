import json
import os
import string

import app
import pathing
import userhandling
from pathing import write_to_error_log, ADMIN_FOLDER


def list_live_files(user: userhandling.UserMethodPack):  # In Admin there exists a file dict
    if not user.exists():
        return []
    if not os.path.isdir(user.admin_directory()):
        return []
    user.acquire_live_files_log_lock()
    # Does the log exist?
    if not os.path.isfile(user.live_files_log_path()):
        user.release_live_files_log_lock()
        return []
    with open(user.live_files_log_path(), 'r') as live_files_log_file:
        data = json.load(live_files_log_file)
    user.release_live_files_log_lock()
    # Obtain the set of names 'live'.
    live_files = []
    for name, isLive in data.items():
        if isLive:
            live_files.append([name, load_additional_data(
                latest_filename_version(name, user), user
            )['nonce1']])
    return live_files


def set_file_liveness(filename: str, set_to: bool, user: userhandling.UserMethodPack):
    if not user.exists():
        return False
    if not os.path.isdir(user.admin_directory()):
        write_to_error_log("File that shouldn't exist's status attempted to be changed by" + user.userID + ".")
        return False  # File doesn't exist.
    user.acquire_live_files_log_lock()
    # Does the log exist?
    if not os.path.isfile(user.live_files_log_path()):
        write_to_error_log("File that shouldn't exist's status attempted to be changed by" + user.userID + ".")
        user.release_live_files_log_lock()
        return False
    with open(user.live_files_log_path(), 'r') as live_files_log_file:
        data = json.load(live_files_log_file)
    # Does the log contain the name?
    if filename not in data.keys():
        user.release_live_files_log_lock()
        return False
    # Set it to 'set_to'.
    data[filename] = set_to
    with open(user.live_files_log_path(), 'w') as live_files_log_file:
        json.dump(data, live_files_log_file)
    user.release_live_files_log_lock()
    return True


def archive_file(filename, user: userhandling.UserMethodPack):
    return set_file_liveness(filename, False, user=user)


def resurrect_file(filename, user:userhandling.UserMethodPack):
    return set_file_liveness(filename, True, user=user)


def mark_file_as_live(filename, user: userhandling.UserMethodPack):
    user.acquire_live_files_log_lock()
    # Does the log exist?
    if not os.path.isdir(ADMIN_FOLDER):
        os.mkdir(ADMIN_FOLDER)
    if not os.path.isdir(user.admin_directory()):
        os.mkdir(user.admin_directory())
    if not os.path.isfile(user.live_files_log_path()):
        with open(user.live_files_log_path(), 'w') as live_log:
            json.dump({filename: True}, live_log)  # First entry.
        user.release_live_files_log_lock()
        return
    with open(user.live_files_log_path(), 'r') as live_log:
        data = json.load(live_log)
    data[filename] = True
    with open(user.live_files_log_path(), 'w') as live_log:
        json.dump(data, live_log)
    user.release_live_files_log_lock()


def save_file_and_additional_data(file, avail_filename, additional_data, user: userhandling.UserMethodPack):  # TODO: How to test this?
    user_upload_dir = user.upload_directory()
    if not os.path.isdir(user_upload_dir):
        os.mkdir(user_upload_dir)
    file.save(os.path.join(user_upload_dir, avail_filename))
    store_additional_data(avail_filename, additional_data, user)


def store_additional_data(server_side_name, additional_data, user: userhandling.UserMethodPack):
    user_admin_dir = user.admin_directory()
    if not os.path.isdir(ADMIN_FOLDER):
        os.mkdir(ADMIN_FOLDER)
    if not os.path.isdir(user_admin_dir):  # If admin dir of user not created ...
        os.mkdir(user_admin_dir)  # ... create it.
    user_add_log_loc = user.add_data_log_path()
    if not os.path.isfile(user_add_log_loc):
        # If the file doesn't already exist, just dump a simple map into it.
        with open(user_add_log_loc, 'w') as add_log:
            json.dump({server_side_name: additional_data}, add_log)
        return
    with open(user_add_log_loc, 'r') as add_log:
        data = json.load(add_log)
    data[server_side_name] = additional_data
    with open(user_add_log_loc, 'w') as add_log:
        json.dump(data, add_log)


def load_file_path_and_additional_data(server_side_name, user: userhandling.UserMethodPack):
    filepath = os.path.join(user.upload_directory(), server_side_name)
    if not os.path.isfile(filepath):
        return None, None
    additional_data = load_additional_data(server_side_name, user)
    if additional_data is None:
        return None, None
    return filepath, additional_data


def load_additional_data(filename, user: userhandling.UserMethodPack):
    user.acquire_additional_data_log_lock()
    # Does the log exist?
    if not os.path.isfile(user.add_data_log_path()):
        user.release_additional_data_log_lock()
        return None
    with open(user.add_data_log_path(), 'r') as add_log:
        data = json.load(add_log)
    user.release_additional_data_log_lock()
    # Does the log contain an entry for our filename?
    if filename not in data.keys():
        return None
    return data[filename]


def load_latest_timestamp(filename, user: userhandling.UserMethodPack):
    latest_filename = latest_filename_version(filename, user)
    additional_data_of_file = load_additional_data(latest_filename, user)  # A bit redundant.
    if additional_data_of_file is None:
        return None
    return additional_data_of_file['t']


def get_available_name(filename, timestamp, user: userhandling.UserMethodPack):
    for i in range(100):
        avail_filename = filename_to_server_side_name(filename, timestamp, i)
        if not os.path.isfile(os.path.join(user.upload_directory(), avail_filename)):
            break
    if os.path.isfile(os.path.join(user.upload_directory(), avail_filename)):
        return None
    return avail_filename


def matching_additional_data(filename, additional_data):
    # For the additional data to match the name has to match
    # and the time cannot be in the future or older than 60 secs. <- Depricated (long time ago)
    if additional_data['n'] == filename:
        return True
    else:
        write_to_error_log("Names doens't match: " + filename + "!=" + additional_data['n'])
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


def latest_filename_version(filename, user: userhandling.UserMethodPack):
    files = os.listdir(user.upload_directory())
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
