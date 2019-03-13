import os
from flask import Flask, request, flash, redirect, send_from_directory, jsonify
from werkzeug.utils import secure_filename

curr_path = os.getcwd()
UPLOAD_FOLDER = curr_path + '/UPLOADS/'
RESOURCE_FOLDER = curr_path + '/resources'
ALLOWED_EXTENSIONS = set(['txt', 'png'])

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
        return jsonify(files)


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if request.method == 'POST':

        if len(request.files) == 0:  # No file
            flash('No file sent along with request.')
            return redirect('/', code=302)

        file = request.files['file']
        if acceptable_file(file.filename) and acceptable_file(secure_filename(file.filename)):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            redirect('/list_files', code=302)
        else:
            flash("Invalid file. Can't accept.")
        return redirect('/', code=302)


@app.route('/get_file/<string:filename_unchecked>', methods=['GET'])
def get_file(filename_unchecked):
    if request.method == 'GET' and acceptable_file(filename_unchecked):
        filename = secure_filename(filename_unchecked)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        else:
            flash("No such file")
            return redirect('/', code=404)
    else:
        flash("Request not understood. Try checking the url.")
        return redirect('/', code=400)


def acceptable_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS and len(filename.rsplit('/')) == 1


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    if not os.path.isdir(UPLOAD_FOLDER):
        raise Exception("No upload folder was reachable. Perhaps", UPLOAD_FOLDER, "already exists.")
    app.run(host='0.0.0.0', port=8000, threaded=True)
