import os
import string
import time

from flask import Flask, request, redirect, send_from_directory, jsonify
from werkzeug.utils import secure_filename

curr_path = os.getcwd()
UPLOAD_FOLDER = curr_path + '/UPLOADS/'
RESOURCE_FOLDER = curr_path + '/resources'
ERROR_LOG = curr_path + '/ERROR_LOG_CIO.txt'
ALLOWED_EXTENSIONS = {'cio'}  # Our madeup fileext indicating that it has been encrypted; not to be confused with SWAT.

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESOURCES'] = RESOURCE_FOLDER
app.config['ERROR_LOG'] = ERROR_LOG


@app.route('/')
def get_main_page():
    return send_from_directory(app.config['RESOURCES'], 'gif.gif', mimetype='image/gif')


@app.route('/favicon.ico')
def get_icon():
    return send_from_directory(app.config['RESOURCES'], 'icon.ico', mimetype='image/ico')


@app.route('/list_files', methods=['GET'])
def get_file_list():
    if request.method == 'GET':
        files = os.listdir(UPLOAD_FOLDER)
        accurate_names = set(map(server_side_name_to_filename, files))  # TODO: Check if correct
        return jsonify(list(accurate_names))


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if request.method == 'POST':

        if len(request.files) == 0:  # No file
            return redirect('/', code=400)

        file = request.files['file']
        filename_unchecked = file.filename
        sec_filename = secure_filename(filename_unchecked)

        if acceptable_file(filename_unchecked) and acceptable_file(sec_filename):
            # Make sure path is available (should be, but check for safety)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename_to_server_side_name(sec_filename))
            for i in range(100):
                if not os.path.exists(path): break
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename_to_server_side_name(sec_filename))
                if i == 100:
                    return redirect('/', code=504)

            file.save()
            return redirect('/list_files', code=302)  # TODO: Perhaps should be changed.

        else:  # Unacceptable filename.

            return redirect('/', code=400)


@app.route('/get_file/<string:filename_unchecked>', methods=['GET'])
def get_file(filename_unchecked):

    sec_filename = secure_filename(filename_unchecked)

    if request.method == 'GET' and acceptable_file(filename_unchecked)\
            and acceptable_file(sec_filename):

        latest_filename = latest_filename_version(sec_filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], latest_filename)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], latest_filename)
        else:
            return redirect('/', code=400)
    else:
        return redirect('/', code=400)


# TODO: (maybe) move, (maybe) archive


@app.route('/rename_file', methods=['POST'])
def rename_file():
    if request.method == 'POST':

        new_filename_unchecked = request.args.get("old_name", None)
        old_filename_unchecked = request.args.get("new_name", None)

        if new_filename_unchecked is None \
                or old_filename_unchecked is None:  # Should have args in request.
            return redirect('/', code=400)

        sec_new_filename = secure_filename(new_filename_unchecked)
        sec_old_filename = secure_filename(old_filename_unchecked)  # get new secure filenames.

        latest_filename = latest_filename_version(sec_new_filename)  # what's the real name of the file?

        if not acceptable_file(new_filename_unchecked) \
                or not acceptable_file(old_filename_unchecked) \
                or not acceptable_file(sec_new_filename) \
                or not acceptable_file(sec_old_filename) \
                or not os.path.exists(UPLOAD_FOLDER + latest_filename) \
                or not os.path.isfile(UPLOAD_FOLDER + latest_filename):
            return redirect('/', code=400)  # Something with the name is bad, or the file doesn't exist.
        # valid names and file exists.
        os.rename(latest_filename,
                  filename_to_server_side_name(sec_new_filename))
        return redirect('/', code=200)
    else:
        return redirect('/', code=400)  # Bad request.


@app.errorhandler(413)
def request_entity_too_large(error):
    write_to_error_log(error)
    return redirect('/', 413)


@app.errorhandler(500)
def internal_server_error(error):
    write_to_error_log(error)
    return redirect('/', 500)


# We're getting the latest filename.
# Recall that names on server are name^numbers.numbers.cio
# while name requested is name.cio
def latest_filename_version(filename):
    files = os.listdir(app.config['UPLOAD_FOLDER'])
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
    if not acceptable_file(filename) or secure_filename(filename) != filename:
        raise Exception("Server asked to translate unsafe filename; won't do that.")

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


def acceptable_file(filename):
    if '.' not in filename: return False
    filename_fragments = filename.rsplit('.', 1)
    if filename_fragments[1].lower() not in ALLOWED_EXTENSIONS: return False
    for char in filename_fragments[0]:
        if char not in string.hexdigits:
            return False
    return True


def write_to_error_log(s:string):
    with open(ERROR_LOG, 'a') as error_log_file:
        error_log_file.write(s)  # Write to the error log


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    if not os.path.isdir(UPLOAD_FOLDER):
        raise Exception("No upload folder was reachable. Perhaps", UPLOAD_FOLDER, "already exists.")
    if not os.path.isfile(ERROR_LOG):
        with open(ERROR_LOG, 'w') as error_log_file:
            error_log_file.write(('-'*5 + ' CloudIO Error Log ' + '-'*5))  # Create the error log

    app.run(host='0.0.0.0', port=8000, threaded=True)
