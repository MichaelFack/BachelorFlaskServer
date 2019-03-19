import os
from flask import Flask, request, flash, redirect, send_from_directory, jsonify
from werkzeug.utils import secure_filename

curr_path = os.getcwd()
UPLOAD_FOLDER = curr_path + '/UPLOADS/'
RESOURCE_FOLDER = curr_path + '/resources'
ALLOWED_EXTENSIONS = {'txt', 'png', 'gif', 'pdf', 'wav'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESOURCES'] = RESOURCE_FOLDER


@app.route('/')
def nothing():
    return send_from_directory(app.config['RESOURCES'], 'gif.gif', mimetype='image/gif')


@app.route('/list_files', methods=['GET'])
def get_file_list():
    if request.method == 'GET':
        files = os.listdir(UPLOAD_FOLDER)
        accurate_names = set(map(latest_filename_version, files))
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

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_to_server_side_name(sec_filename)))
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


# TODO: (maybe) move, (maybe) archive, name differentiation


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
    return redirect('/', 413)


# used in implementing name differentiation - whenever we store a file append current local time.
def latest_filename_version(filename):
    return filename  # TODO: get latest filename version


def filename_to_server_side_name(filename):
    return filename  # TODO: name differentiation


def server_side_name_to_filename(server_side_name):
    return server_side_name  # TODO: reverse name differentiation


def acceptable_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS and len(
        filename.rsplit('/')) == 1


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024

    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    if not os.path.isdir(UPLOAD_FOLDER):
        raise Exception("No upload folder was reachable. Perhaps", UPLOAD_FOLDER, "already exists.")
    app.run(host='0.0.0.0', port=8000, threaded=True)
