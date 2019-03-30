import os
import string
import time

from werkzeug.utils import secure_filename

import app


def get_filenames_from_serversidenames_stored():
    files = os.listdir(app.UPLOAD_FOLDER)
    accurate_names = set(map(server_side_name_to_filename, files))  # TODO: Check if correct
    return list(accurate_names)


def save_file_as(file, filename):
    file.save(os.path.join(app.UPLOAD_FOLDER, filename))


def get_available_name(sec_filename):
    success = True
    avail_filename = filename_to_server_side_name(sec_filename)
    path = os.path.join(app.UPLOAD_FOLDER, avail_filename)
    for i in range(100):
        if not os.path.exists(path): break
        avail_filename = filename_to_server_side_name(sec_filename)
        path = os.path.join(app.UPLOAD_FOLDER, avail_filename)
        if i == 100:
            success = False
            avail_filename = None
    return avail_filename, success


def rename_file(latest_filename, sec_new_filename):
    avail_name, success = get_available_name(sec_new_filename)
    if success:
        os.rename(os.path.join(app.UPLOAD_FOLDER, latest_filename), os.path.join(app.UPLOAD_FOLDER, avail_name))
    else:
        app.write_to_error_log('Could not determine available name for file "'
                           + latest_filename + '" as "' + sec_new_filename + '".')
    return success


# We're getting the latest filename.
# Recall that names on server are name^numbers.numbers.cio
# while name requested is name.cio
def latest_filename_version(filename):
    files = os.listdir(app.UPLOAD_FOLDER)
    filename_prefix = filename.split('.')[0]  # name part of request
    curr_latest_filename = None
    curr_timestamp = 0.0
    for filename_of_list in files:
        if filename_prefix == filename_of_list.split('_', 1)[0]:  # name == name
            numbers = filename_of_list.rsplit('_', 1)[1].rsplit('.', 2)
            file_timestamp = float(numbers[0] + '.' + numbers[1])  # reconstruct number.number as float
            if curr_latest_filename is None or curr_timestamp < file_timestamp:
                curr_latest_filename = filename_of_list
                curr_timestamp = file_timestamp
    return curr_latest_filename


def filename_to_server_side_name(filename):
    # Lets be defensive and assert that the name is safe:
    if not acceptable_filename(filename) or secure_filename(filename) != filename:
        raise Exception("Server was asked to translate unsafe filename; won't do that.")

    # Now we pull the name apart and ...
    filename_fragments = filename.split('.', 1)
    # ... put it back together with _[time.time()] before the file extension
    time_now = time.time()
    server_side_name = filename_fragments[0] + "_" + str(time_now) + '.' + filename_fragments[1]

    return server_side_name


def server_side_name_to_filename(server_side_name):
    # Split up the server_side_name to remove the time.time()
    server_side_name_fragments = server_side_name.rsplit('_')
    fragment_amount = len(server_side_name_fragments)
    server_side_name_suffix = server_side_name_fragments[fragment_amount - 1]
    file_ext = server_side_name_suffix.rsplit('.')[-1]  # ext is the last bit

    # Put it all back together.
    filename = server_side_name_fragments[0]
    for idx in range(1, fragment_amount - 2):
        filename += '_' + server_side_name_fragments[idx]
    filename += '.' + file_ext

    return filename


def acceptable_filename(filename):
    if '.' not in filename: return False
    filename_fragments = filename.rsplit('.', 1)
    if filename_fragments[1].lower() not in app.ALLOWED_EXTENSIONS: return False
    for char in filename_fragments[0]:
        if char not in string.hexdigits:
            return False
    return True
