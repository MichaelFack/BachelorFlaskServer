import json
import os

from flask import Flask, request, send_from_directory, jsonify, Response, make_response, send_file
from flask_login import LoginManager, login_user

import filehandling
import userhandling

curr_path = os.getcwd()
UPLOAD_FOLDER = os.path.join(curr_path, 'UPLOADS')
RESOURCE_FOLDER = os.path.join(curr_path, 'resources')
ADMIN_FOLDER = os.path.join(curr_path, 'ADMIN')
ERROR_LOG = os.path.join(curr_path, 'ADMIN', 'ERROR_LOG_CIO.txt')
USER_CATALOG = os.path.join(curr_path, 'ADMIN', 'USERS.txt')  # TODO: Move to user handling?
USER_RECENT_CHALLENGES = os.path.join(curr_path, 'ADMIN', 'CHALLENGES.txt')
LIVE_FILES_LOG = os.path.join(ADMIN_FOLDER, 'LIVE_FILES.txt')  # dict[name->bool(isLive)]
ADDITIONAL_DATA_LOG = os.path.join(ADMIN_FOLDER, 'ADD_DATA_LOG.txt')  # dict[avail_name->(filename, timestamp)]
ALLOWED_EXTENSIONS = {'cio'}  # Our madeup fileext indicating that it has been encrypted; not to be confused with SWAT.
LOGIN_CHALLENGE_LENGTH = 32


def bad_request(): return Response(status=400)


def successful_request(): return Response(status=200)


def internal_server_error_response(): return Response(status=500)


def file_not_found_response(): return Response(status=404)


app = Flask(__name__)
login_manager = LoginManager()


@app.route('/')
def get_main_page():
    return send_from_directory(RESOURCE_FOLDER, 'gif.gif', mimetype='image/gif')


@app.route('/favicon.ico')
def get_icon():
    return send_from_directory(RESOURCE_FOLDER, 'icon.ico', mimetype='image/ico')


@app.route('/list_files', methods=['GET'])
def list_files():
    if request.method != 'GET':
        return bad_request()
    return jsonify({'file_list': filehandling.list_live_files()})


@app.route('/upload_file', methods=['POST'])
def upload_file():
    # Is it the right method?
    if request.method != 'POST':
        return bad_request()
    # Does it contain files?
    if len(request.files) == 0:  # No file
        print("No files")
        return bad_request()
    # Does it contain the 'file'?
    if 'file_content' not in request.files.keys():
        print("File not included")
        return bad_request()
    file = request.files['file_content']
    # Does it contain additional data?
    if 'additional_data' not in request.files.keys():
        print("additional_data not included")
        return bad_request()
    additional_data = json.loads(request.files['additional_data'].read().decode('utf-8'))
    filename = file.filename
    # Does the additional data match?
    additional_data_matches = filehandling.matching_additional_data(filename, additional_data)
    # Is the filename secure?
    is_acceptable_filename = filehandling.acceptable_filename(filename)
    if not additional_data_matches or not is_acceptable_filename:
        print("additional_data_matches=", additional_data_matches, "acceptable_name=", is_acceptable_filename)
        return bad_request()
    # If all this is, then we can start working; first we find an available name for local storage:
    avail_filename = filehandling.get_available_name(filename, additional_data['t'])  # TODO: fix this method
    # If we could not log the error and return.
    if avail_filename is None:
        return internal_server_error_logging('Could not find available name for file:' + filename)
    # Save the file and the additional data under the filename.
    filehandling.mark_file_as_live(filename)
    filehandling.save_file_and_additional_data(file, avail_filename, additional_data)  # TODO: fix this method
    return successful_request()  # TODO: Consider returning a receipt such that client can prove a file was stored.


@app.route('/get_file/<string:filename>', methods=['GET'])
def get_file(filename):
    # Is the filename requested legit?
    is_filename_acceptable = filehandling.acceptable_filename(filename)
    if request.method != 'GET' or not is_filename_acceptable:
        return bad_request()
    # what is the latest version's name of this file?
    latest_filename = filehandling.latest_filename_version(filename)
    if latest_filename is None:
        return file_not_found_response()
    # return the file and its associated additional data. If this doesn't match our client will be sad :(
    file_path, additional_data = filehandling.load_file_path_and_additional_data(latest_filename)  # TODO: fix this method
    if file_path is None or additional_data is None:
        return file_not_found_response()
    with open(file_path, 'rb') as file:
        file_content = file.read().hex()
    return json.dumps({'file': file_content, 'additional_data': additional_data})


@app.route('/get_file/<string:filename>', methods=['GET'])
def get_file_timestamp(filename):
    # Is the filename requested legit?
    is_filename_acceptable = filehandling.acceptable_filename(filename)
    if request.method != 'GET' or not is_filename_acceptable:
        return bad_request()
    # what is the latest version's name of this file?
    latest_filename = filehandling.latest_filename_version(filename)
    if latest_filename is None:
        return file_not_found_response()
    # Get the timestamp of it and return it.
    return filehandling.load_latest_timestamp(latest_filename)  # TODO: fix this method


# TODO: Remove this method after verifying with Da Sawsasche
@app.route('/rename_file', methods=['POST'])
def rename_file_request():
    return bad_request()
    # How the hell is the server supposed to be able to rename a file when the client has the name encrypted??
'''
    # Is the request right kind?
    if request.method != 'POST':
        return bad_request()
    # Does it have the right arguements?
    new_filename = request.args.get("old_name", None)
    old_filename = request.args.get("new_name", None)
    is_new_name_acceptable = filehandling.acceptable_filename(new_filename)
    is_old_name_acceptable = filehandling.acceptable_filename(old_filename)

    if new_filename is None or old_filename is None:  # Should have args in request.
        return bad_request()

    latest_filename = filehandling.latest_filename_version(old_filename)  # what's the real name of the file?

    if not filehandling.acceptable_filename(new_filename_unchecked) \
            or not filehandling.acceptable_filename(old_filename_unchecked) \
            or not filehandling.acceptable_filename(sec_new_filename) \
            or not filehandling.acceptable_filename(sec_old_filename) \
            or not os.path.isfile(os.path.join(UPLOAD_FOLDER, latest_filename)):
        return bad_request()  # Something with the name is bad, or the file doesn't exist.
    # valid names and file exists.
    success = filehandling.rename_file(latest_filename, sec_new_filename)
    if success:
        return successful_request()
    else:
        return internal_server_error_response()
'''


@app.errorhandler(413)
def request_entity_too_large_logging(error):
    write_to_error_log(error)
    return bad_request()


@app.errorhandler(404)
def not_found_logging(error):
    write_to_error_log(error)
    return bad_request()


@app.errorhandler(500)
def internal_server_error_logging(error):
    write_to_error_log(error)
    return internal_server_error_response()


def write_to_error_log(s):  # We're imperfect beings and our code may reflect this. Log your errors.
    if type(s) is not str:
        s = str(s)
    with open(ERROR_LOG, 'a') as error_log_file:
        error_log_file.write('\n' + s)  # Write to the error log


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':  # To login you first get a challenge.
        # Regardless of whether a user exists or not we should issue a challenge;
        # can't let people know who is users and who aren't.
        # If we return a challenge only when you've input a valid user_id adversaries may guess user_ids
        user_id = request.args.get('user_id', None)
        return userhandling.issue_challenge(user_id)  # TODO: Ensure always issues challenges, even when user_id is invalid.
    elif request.method == 'POST':  # Then you respond to that challenge.
        # When one responds to a challenge always return bad request lest the request is well formed and validate.
        user_id = request.args.get('user_id', None)
        if user_id is None:
            return bad_request()
        challenge_response = request.args.get('challenge_response', None)
        if challenge_response is None:
            return bad_request()
        latest_challenge = userhandling.get_latest_challenge(user_id)
        if latest_challenge is None:
            return bad_request()
        if userhandling.validate_challenge_response(user_id, latest_challenge, challenge_response):
            login_user(user_id)
            return successful_request()
        return bad_request()
    return bad_request()  # Should not happen; flask denies request of wrong method.


@app.route('/archive_file/<string:filename>', methods=['POST'])
def archive_file(filename):
    if request.method != 'POST':
        return bad_request()
    if not filehandling.acceptable_filename(filename):
        return bad_request()
    success = filehandling.archive(filename)  # TODO: Implement this
    if success:
        return successful_request()
    else:
        return file_not_found_response()


@app.route('/resurrect_file/<string:filename>', methods=['POST'])
def resurrect_file(filename):
    if request.method != 'POST':
        return bad_request()
    if not filehandling.acceptable_filename(filename):
        return bad_request()
    success = filehandling.resurrect(filename)  # TODO: Implement this
    if success:
        return successful_request()
    else:
        return file_not_found_response()


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
