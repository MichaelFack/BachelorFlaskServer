import json
import os

from flask import Flask, request, send_from_directory, jsonify, Response
from flask_login import LoginManager

import filehandling
import userhandling
from pathing import write_to_error_log, RESOURCE_DIR, ADMIN_FOLDER, UPLOAD_FOLDER, ERROR_LOG

ALLOWED_EXTENSIONS = {'cio'}  # Our madeup fileext indicating that it has been encrypted; not to be confused with SWAT.


def bad_request(): return Response(status=400)


def successful_request(): return Response(status=200)


def internal_server_error_response(): return Response(status=500)


def file_not_found_response(): return Response(status=404)


app = Flask(__name__)
login_manager = LoginManager()


@app.route('/')
def get_main_page():
    return send_from_directory(RESOURCE_DIR, 'gif.gif', mimetype='image/gif')


@app.route('/favicon.ico')
def get_icon():
    return send_from_directory(RESOURCE_DIR, 'icon.ico', mimetype='image/ico')


@app.route('/list_files/<string:userID>', methods=['GET'])
def list_files(userID: str):
    if request.method != 'GET':
        return bad_request()
    user = userhandling.UserMethodPack(userID)
    if not user.exists():
        return jsonify({'file_list': []})
    return jsonify({'file_list': filehandling.list_live_files(user)})


@app.route('/upload_file/<string:userID>', methods=['POST'])
def upload_file(userID: str):
    # Is it the right method?
    if request.method != 'POST':  # TODO: Remove? Should be handled by flask.
        return bad_request()
    # Is it by a legit user?
    user = userhandling.UserMethodPack(userID)
    if not user.exists():
        return bad_request()
    # Does it contain files?
    if len(request.files) == 0:  # No file
        write_to_error_log("Upload file request by " + userID + "without any file.")
        return bad_request()
    # Does it contain the 'file'?
    if 'file_content' not in request.files.keys():
        write_to_error_log("Upload file request by " + userID + "without file.")
        return bad_request()
    file = request.files['file_content']
    # Does it contain additional data?
    if 'additional_data' not in request.files.keys():
        write_to_error_log("Upload file request by " + userID + "without additional data.")
        return bad_request()
    additional_data = json.loads(request.files['additional_data'].read().decode('utf-8'))
    for field in list(additional_data.keys()):
        if field not in ['n', 't', 'nonce1', 'nonce2']:
            return bad_request()
    for field in ['n', 't', 'nonce1', 'nonce2']:
        if field not in list(additional_data.keys()):
            return bad_request()
    filename = file.filename
    # Does the additional data match?
    additional_data_matches = filehandling.matching_additional_data(filename, additional_data)
    # Is the filename secure?
    is_acceptable_filename = filehandling.acceptable_filename(filename)
    if not additional_data_matches or not is_acceptable_filename:
        return bad_request()
    # If all this is, then we can start working; first we find an available name for local storage:
    avail_filename = filehandling.get_available_name(filename, additional_data['t'], user)
    # If we could not log the error and return.
    if avail_filename is None:
        return internal_server_error_logging('Could not find available name for file:' + filename)
    # Save the file and the additional data under the filename.
    filehandling.mark_file_as_live(filename, user)
    filehandling.save_file_and_additional_data(file, avail_filename, additional_data, user=user)
    return successful_request()  # TODO: Consider returning a receipt such that client can prove a file was stored.


@app.route('/get_file/<string:filename>/<string:userID>', methods=['GET'])
def get_file(filename, userID):
    # Is the filename requested legit?
    is_filename_acceptable = filehandling.acceptable_filename(filename)
    if request.method != 'GET' or not is_filename_acceptable:
        return bad_request()
    # what is the latest version's name of this file?
    user = userhandling.UserMethodPack(userID)
    if not user.exists():
        return file_not_found_response()  # Obscure that user doens't exist
    latest_filename = filehandling.latest_filename_version(filename, user)
    if latest_filename is None:
        return file_not_found_response()
    # return the file and its associated additional data. If this doesn't match our client will be sad :(
    file_path, additional_data = filehandling.load_file_path_and_additional_data(latest_filename, user)
    if file_path is None or additional_data is None:
        return file_not_found_response()
    with open(file_path, 'rb') as file:
        file_content = file.read().hex()
    return json.dumps({'file': file_content, 'additional_data': additional_data})


@app.route('/get_file_time/<string:filename>/<string:userID>', methods=['GET'])
def get_file_timestamp(filename, userID):
    # Is the filename requested legit?
    is_filename_acceptable = filehandling.acceptable_filename(filename)
    if request.method != 'GET' or not is_filename_acceptable:
        return bad_request()
    user = userhandling.UserMethodPack(userID)
    if not user.exists():
        return file_not_found_response()
    timestamp = filehandling.load_latest_timestamp(filename, user)
    if timestamp is None:
        return file_not_found_response()
    return timestamp


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


@app.route('/archive_file/<string:filename>/<string:userID>', methods=['POST'])
def archive_file(filename, userID):
    if request.method != 'POST':
        return bad_request()
    if not filehandling.acceptable_filename(filename):
        return bad_request()
    user = userhandling.UserMethodPack(userID)
    if not user.exists():
        return file_not_found_response()
    success = filehandling.archive_file(filename, user)
    if success:
        return successful_request()
    else:
        return file_not_found_response()


@app.route('/resurrect_file/<string:filename>/<string:userID>', methods=['POST'])
def resurrect_file(filename, userID):
    if request.method != 'POST':
        return bad_request()
    if not filehandling.acceptable_filename(filename):
        return bad_request()
    user = userhandling.UserMethodPack(userID)
    if not user.exists():
        return file_not_found_response()
    success = filehandling.resurrect_file(filename, user)
    if success:
        return successful_request()
    else:
        return file_not_found_response()


# TODO: Implement users can change identification.
# def register_alias(userID, userID)


@app.route('/register/<string:userID>', methods=['POST'])
def register_user(userID):
    write_to_error_log("Warning - User was registered by self:" + userID)
    user = userhandling.UserMethodPack(userID)
    if not user.exists():
        user.register()
        return successful_request()
    else:
        return bad_request()


@app.route('/unregister/<string:userID>', methods=['POST'])
def unregister_user(userID):
    write_to_error_log("Warning - User was unregistered by self:" + userID)
    user = userhandling.UserMethodPack(userID)
    if user.exists():
        user.unregister()
        return successful_request()
    else:
        return bad_request()


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

    app.run(host='0.0.0.0', port=8001, threaded=True)
