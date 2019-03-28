import json
import os
import secrets
import string
import time

from flask import Flask, request, redirect, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user

curr_path = os.getcwd()
UPLOAD_FOLDER = os.path.join(curr_path, 'UPLOADS')
RESOURCE_FOLDER = os.path.join(curr_path, 'resources')
ADMIN_FOLDER = os.path.join(curr_path, 'ADMIN')
ERROR_LOG = os.path.join(curr_path, 'ADMIN', 'ERROR_LOG_CIO.txt')  # TODO: Might leak info?
USER_CATALOG = os.path.join(curr_path, 'ADMIN', 'USERS.txt')  # TODO: Consider encrypting this somehow?
USER_RECENT_CHALLENGES = os.path.join(curr_path, 'ADMIN', 'CHALLENGES.txt')
ALLOWED_EXTENSIONS = {'cio'}  # Our madeup fileext indicating that it has been encrypted; not to be confused with SWAT.
LOGIN_CHALLENGE_LENGTH = 32


app = Flask(__name__)
login_manager = LoginManager()


@app.route('/')
def get_main_page():
    return send_from_directory(RESOURCE_FOLDER, 'gif.gif', mimetype='image/gif')


@app.route('/favicon.ico')
def get_icon():
    return send_from_directory(RESOURCE_FOLDER, 'icon.ico', mimetype='image/ico')


@app.route('/list_files', methods=['GET'])
def get_list_files_response():
    if request.method == 'GET':
        return jsonify(get_filenames_from_serversidenames_stored())


def get_filenames_from_serversidenames_stored():
    files = os.listdir(UPLOAD_FOLDER)
    accurate_names = set(map(server_side_name_to_filename, files))  # TODO: Check if correct
    return list(accurate_names)


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if request.method == 'POST':

        if len(request.files) == 0:  # No file
            return redirect('/', code=400)

        file = request.files['file']
        filename_unchecked = file.filename
        sec_filename = secure_filename(filename_unchecked)

        if acceptable_filename(filename_unchecked) and acceptable_filename(sec_filename):
            # Make sure path is available (should be, but check for safety)
            avail_filename, success = get_available_name(sec_filename)

            if success:
                save_file_as(file, avail_filename)
                return redirect('/list_files', code=302)  # TODO: Perhaps should be changed.
            else:
                return redirect('/', code=504)  # Should never happen, probably.

        else:  # Unacceptable filename.
            return redirect('/', code=400)


def save_file_as(file, filename):
    file.save(os.path.join(UPLOAD_FOLDER, filename))


def get_available_name(sec_filename):
    success = True
    avail_filename = filename_to_server_side_name(sec_filename)
    path = os.path.join(UPLOAD_FOLDER, avail_filename)
    for i in range(100):
        if not os.path.exists(path): break
        avail_filename = filename_to_server_side_name(sec_filename)
        path = os.path.join(UPLOAD_FOLDER, avail_filename)
        if i == 100:
            success = False
            avail_filename = None
    return avail_filename, success


@app.route('/get_file/<string:filename_unchecked>', methods=['GET'])
def get_file(filename_unchecked):

    sec_filename = secure_filename(filename_unchecked)

    if request.method == 'GET' and acceptable_filename(filename_unchecked)\
            and acceptable_filename(sec_filename):

        latest_filename = latest_filename_version(sec_filename)
        file_path = os.path.join(UPLOAD_FOLDER, latest_filename)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(UPLOAD_FOLDER, latest_filename)
        else:
            return redirect('/', code=400)
    else:
        return redirect('/', code=400)


# TODO: (maybe) move, (maybe) archive


@app.route('/rename_file', methods=['POST'])
def rename_file_request():
    if request.method == 'POST':

        new_filename_unchecked = request.args.get("old_name", None)
        old_filename_unchecked = request.args.get("new_name", None)

        if new_filename_unchecked is None \
                or old_filename_unchecked is None:  # Should have args in request.
            return redirect('/', code=400)

        sec_new_filename = secure_filename(new_filename_unchecked)
        sec_old_filename = secure_filename(old_filename_unchecked)  # get new secure filenames.

        latest_filename = latest_filename_version(sec_old_filename)  # what's the real name of the file?

        if not acceptable_filename(new_filename_unchecked) \
                or not acceptable_filename(old_filename_unchecked) \
                or not acceptable_filename(sec_new_filename) \
                or not acceptable_filename(sec_old_filename) \
                or not os.path.isfile(os.path.join(UPLOAD_FOLDER, latest_filename)):
            return redirect('/', code=400)  # Something with the name is bad, or the file doesn't exist.
        # valid names and file exists.
        success = rename_file(latest_filename, sec_new_filename)
        if success:
            return redirect('/', code=200)
        else:
            return redirect('/', code=502)
    else:
        return redirect('/', code=400)  # Bad request.


def rename_file(latest_filename, sec_new_filename):
    avail_name, success = get_available_name(sec_new_filename)
    if success:
        os.rename(os.path.join(UPLOAD_FOLDER, latest_filename), os.path.join(UPLOAD_FOLDER, avail_name))
    else:
        write_to_error_log('Could not determine available name for file "'
                           + latest_filename + '" as "' + sec_new_filename + '".')
    return success


@app.errorhandler(413)
def request_entity_too_large(error):
    write_to_error_log(error)
    return redirect('/', 413)


@app.errorhandler(404)
def not_found(error):
    write_to_error_log(error)
    redirect('/', code=404)


@app.errorhandler(500)
def internal_server_error(error):
    write_to_error_log(error)
    return redirect('/', 500)


# We're getting the latest filename.
# Recall that names on server are name^numbers.numbers.cio
# while name requested is name.cio
def latest_filename_version(filename):
    files = os.listdir(UPLOAD_FOLDER)
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
    if filename_fragments[1].lower() not in ALLOWED_EXTENSIONS: return False
    for char in filename_fragments[0]:
        if char not in string.hexdigits:
            return False
    return True


def write_to_error_log(s):
    if type(s) is not str:
        s = str(s)
    with open(ERROR_LOG, 'a') as error_log_file:
        error_log_file.write('\n' + s)  # Write to the error log


@app.route('/login', methods=['GET', 'POST'])  # Step 1 in login in; being issued a challenge.
def login():
    if request.method == 'GET':
        user_id = request.args.get('user_id', None)
        challenge = issue_challenge(user_id)
        return challenge
    elif request.method == 'POST':
        user_id = request.args.get('user_id', None)
        if user_id is None:
            redirect('/', code=401)
        challenge_response = request.args.get('challenge_response', None)
        if challenge_response is None:
            redirect('/', code=401)
        latest_challenge = get_latest_challenge(user_id)
        if latest_challenge is None:
            redirect('/', code=401)
        if valid_challenge_response(user_id, latest_challenge, challenge_response):
            login_user(user_id)
            return redirect('/', code=200)
        return redirect('/', code=401)
    return redirect('/', code=400)  # Should not happen; flask denies request of wrong method.


def issue_challenge(user_id):
    challenge_time = time.time()
    challenge = secrets.token_hex(LOGIN_CHALLENGE_LENGTH)
    if user_exists(user_id):
        log_latest_challenge(user_id, challenge, challenge_time)
    return challenge


def user_exists(USER_IDENTIFIER):
    for user in get_users():  # Should be fine as long as |users| < a lot
        if user.USER_IDENTIFIER == USER_IDENTIFIER:
            return True
    return False


def get_users():
    if not os.path.isfile(USER_CATALOG):
        return []
    with open(USER_CATALOG, 'r') as file:
        return json.load(file)


def log_latest_challenge(USER_IDENTIFIER, challenge, challenge_time):
    pass  # TODO


def get_latest_challenge(USER_IDENTIFIER):
    pass  # TODO


def valid_challenge_response(user_id, latest_challenge, challenge_response):
    pass  # TODO


def create_user(USER_IDENTIFIER, HASH_IDENTIFIER):
    if not os.path.isfile(USER_CATALOG):
        with open(USER_CATALOG, 'w+') as file:
            json.dump([(USER_IDENTIFIER, HASH_IDENTIFIER)], file)
    else:
        with open(USER_CATALOG, 'r') as file:
            users = json.load(file)  # List?
        if USER_IDENTIFIER in map(lambda x: x[0], users):
            return False
        users.append((USER_IDENTIFIER, HASH_IDENTIFIER))
        with open(USER_CATALOG, 'w') as file:
            json.dump(users, file)
    return True


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
    login_manager.init_app(app)

    if not os.path.exists(ADMIN_FOLDER):
        os.mkdir(ADMIN_FOLDER)
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    if not os.path.isdir(UPLOAD_FOLDER):
        raise Exception("No upload folder was reachable. Perhaps", UPLOAD_FOLDER, "already exists.")
    if not os.path.isfile(ERROR_LOG):
        with open(ERROR_LOG, 'w') as error_log_file:  # Errorlog should exist.
            error_log_file.write(('-'*5 + ' CloudIO Error Log ' + '-'*5))  # Create the error log

    app.run(host='0.0.0.0', port=8000, threaded=True)
