import pathlib as pl
PROJECT_NAME = "CloudIOServer"


def get_CloudIOServer_path():
    curr_dir = pl.Path.cwd()
    if curr_dir.name == PROJECT_NAME:
        return curr_dir
    idx = 0
    while curr_dir.parents[idx].name != PROJECT_NAME:
        idx += 1
    return curr_dir.parents[idx]


WORK_DIR = get_CloudIOServer_path()
RESOURCE_DIR = pl.Path.joinpath(WORK_DIR, 'resources')
UPLOAD_FOLDER = pl.Path.joinpath(WORK_DIR, 'uploads')
ADMIN_FOLDER = pl.Path.joinpath(WORK_DIR, 'admin')
ERROR_LOG = pl.Path.joinpath(ADMIN_FOLDER, 'error_log.txt')
USER_CATALOG = pl.Path.joinpath(ADMIN_FOLDER, 'users.txt')


def write_to_error_log(s):  # We're imperfect beings and our code may reflect this. Log your errors.
    if type(s) is not str:
        s = str(s)
    with open(ERROR_LOG, 'a') as error_log_file:
        error_log_file.write('\n' + s)  # Write to the error log


LIVE_FILES_LOG_FILENAME = 'LIVE_FILES.txt'  # dict[name->bool(isLive)]
ADDITIONAL_DATA_LOG_FILENAME = 'ADD_DATA_LOG.txt'  # dict[avail_name->(filename, timestamp)]
