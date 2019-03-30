import os

from flask import Flask, request, redirect, send_from_directory, jsonify, Response
from flask_login import LoginManager, login_user
from werkzeug.utils import secure_filename

import filehandling
import userhandling

curr_path = os.getcwd()
UPLOAD_FOLDER = os.path.join(curr_path, 'UPLOADS')
RESOURCE_FOLDER = os.path.join(curr_path, 'resources')
ADMIN_FOLDER = os.path.join(curr_path, 'ADMIN')
ERROR_LOG = os.path.join(curr_path, 'ADMIN', 'ERROR_LOG_CIO.txt')  # TODO: Might leak info?
USER_CATALOG = os.path.join(curr_path, 'ADMIN', 'USERS.txt')  # TODO: Consider encrypting this somehow?
USER_RECENT_CHALLENGES = os.path.join(curr_path, 'ADMIN', 'CHALLENGES.txt')
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
def get_list_files_response():
    if request.method == 'GET':
        return jsonify({'file_list': filehandling.get_filenames_from_serversidenames_stored()})


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if request.method == 'POST':

        if len(request.files) == 0:  # No file
            return redirect('/', code=400)

        file = request.files['file']
        filename_unchecked = file.filename
        sec_filename = secure_filename(filename_unchecked)

        if filehandling.acceptable_filename(filename_unchecked) and filehandling.acceptable_filename(sec_filename):
            # Make sure path is available (should be, but check for safety)
            avail_filename, success = filehandling.get_available_name(sec_filename)

            if success:
                filehandling.save_file_as(file, avail_filename)
                return successful_request()  # TODO: Perhaps should be changed.
            else:
                return internal_server_error_response()  # Should never happen, probably.

        else:  # Unacceptable filename.
            return bad_request()


@app.route('/get_file/<string:filename_unchecked>', methods=['GET'])
def get_file(filename_unchecked):

    sec_filename = secure_filename(filename_unchecked)

    if request.method == 'GET' and filehandling.acceptable_filename(filename_unchecked)\
            and filehandling.acceptable_filename(sec_filename):

        latest_filename = filehandling.latest_filename_version(sec_filename)
        file_path = os.path.join(UPLOAD_FOLDER, latest_filename)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(UPLOAD_FOLDER, latest_filename)
        else:
            return file_not_found_response()
    else:
        return bad_request()


# TODO: (maybe) move, (maybe) archive


@app.route('/rename_file', methods=['POST'])
def rename_file_request():
    if request.method == 'POST':

        new_filename_unchecked = request.args.get("old_name", None)
        old_filename_unchecked = request.args.get("new_name", None)

        if new_filename_unchecked is None \
                or old_filename_unchecked is None:  # Should have args in request.
            return bad_request()

        sec_new_filename = secure_filename(new_filename_unchecked)
        sec_old_filename = secure_filename(old_filename_unchecked)  # get new secure filenames.

        latest_filename = filehandling.latest_filename_version(sec_old_filename)  # what's the real name of the file?

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
    else:
        return bad_request()


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


def write_to_error_log(s):
    if type(s) is not str:
        s = str(s)
    with open(ERROR_LOG, 'a') as error_log_file:
        error_log_file.write('\n' + s)  # Write to the error log


@app.route('/login', methods=['GET', 'POST'])  # Step 1 in login in; being issued a challenge.
def login():
    if request.method == 'GET':
        user_id = request.args.get('user_id', None)
        challenge = userhandling.issue_challenge(user_id)
        return challenge
    elif request.method == 'POST':
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
