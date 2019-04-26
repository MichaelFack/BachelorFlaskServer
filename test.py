import json
import os
import random
import string
import unittest

import numpy as np

import app
import filehandling
import userhandling


class TestFileNaming(unittest.TestCase):
    def setUp(self):
        self.user = userhandling.UserMethodPack("aaaabbbbcccc")
        self.user.register()

    def tearDown(self):
        files_to_rm = []
        if os.path.isdir(self.user.upload_directory()):
            files_to_rm = [os.path.join(self.user.upload_directory(), path) for path in os.listdir(self.user.upload_directory())]
        if os.path.isdir(self.user.admin_directory()):
            files_to_rm += [os.path.join(self.user.admin_directory(), path) for path in os.listdir(self.user.admin_directory())]
        for path in files_to_rm:
            os.remove(path)
        if os.path.isdir(self.user.upload_directory()):
            os.rmdir(self.user.upload_directory())
        if os.path.isdir(self.user.admin_directory()):
            os.rmdir(self.user.admin_directory())
        self.user.unregister()

    def test_accepts_acceptable_names(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.cio'
            self.assertTrue(filehandling.acceptable_filename(s))

    def test_rejects_unacceptable_file_ext(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.'
            ext = ''.join(random.choices(string.ascii_lowercase))
            if ext == 'cio':
                continue
            s += ext
            self.assertFalse(filehandling.acceptable_filename(s))

    def test_rejects_unacceptable_filename(self):
        for i in range(10000):
            n = random.randint(16, 20)
            s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))
            has_illegal_symb = False
            for char in s:
                if char not in string.hexdigits:
                    has_illegal_symb = True
                    break
            if not has_illegal_symb:
                continue
            ext = '.cio'
            s += ext
            self.assertFalse(filehandling.acceptable_filename(s))

    def test_filenames_converted_to_server_side_name_can_be_converted_back(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.cio'
            ssn = filehandling.filename_to_server_side_name(s, 1.0, 0)
            s_ = filehandling.server_side_name_to_filename(ssn)
            self.assertTrue(s == s_, s + " != " + s_+ " where ssn = " + ssn)

    def test_list_files_gets_list_of_unique_file(self):
        # Create a bunch of files with random names
        for i in range(10):
            self.create_test_file('A'+str(i)+'.cio', 1.0)
            self.create_test_file('A'+str(i)+'.cio', 5.0)
            self.create_test_file('AB'+str(i)+'.cio', 1.0)
            self.create_test_file('AB'+str(i)+'.cio', 5.0)
            self.create_test_file('AB'+str(i)+'.cio', 100.0)
        # get the actual names of the files.
        filenames_in_dir = os.listdir(self.user.upload_directory())
        self.assertTrue(len(filenames_in_dir) == 50, str(len(filenames_in_dir)) + " of 50 files created.")
        files_listed_uniquely = list(np.array(filehandling.list_live_files(self.user))[:, 0])
        self.check_server_side_names_are_listed_uniquely(files_listed_uniquely, filenames_in_dir)

    def check_server_side_names_are_listed_uniquely(self, files_listed_uniquely, filenames_in_dir):
        file_names_seen = []
        for file_named in filenames_in_dir:
            self.assertTrue(filehandling.server_side_name_to_filename(file_named) in files_listed_uniquely,
                            "Expected " + file_named
                            + " to be in file_list as "
                            + filehandling.server_side_name_to_filename(file_named))
            self.assertFalse(file_named in file_names_seen)
            file_names_seen.append(file_named)

    def test_get_latest_gets_latest(self):
        self.create_test_file('A.cio', 1.0)
        self.create_test_file('A.cio', 5.0)
        self.create_test_file('A.cio', 99.99)
        self.create_test_file('A.cio', 5.0)
        self.create_test_file('A.cio', 100.0)
        self.assertTrue(filehandling.latest_filename_version('A.cio', self.user) == 'A_100.0_0.cio',
                        "Latest should be 'A_100.0_0.cio' but is" + filehandling.latest_filename_version('A.cio', self.user))

    # def test_can_save_file(self):  # TODO: Write this test.

    def test_new_files_are_listed_uniquely(self):
        for i in range(100):
            self.create_test_file("ABC"+str(i)+".cio", 1.0)
        files_listed_uniquely = list(np.array(filehandling.list_live_files(self.user))[:, 0])
        self.create_test_file('A.cio', 1.0)
        files_listed_uniquely_with_new_file = list(np.array(filehandling.list_live_files(self.user))[:, 0])
        self.assertFalse(files_listed_uniquely == files_listed_uniquely_with_new_file,
                         'Expected new file to have been added.')
        for name in files_listed_uniquely_with_new_file:
            self.assertTrue(name in files_listed_uniquely or name == 'A.cio',
                            'Expect ' + name + ' in previous listing or to be the newly added.')

    def create_test_file(self, test_file_name, timestamp):
        avail_filename = filehandling.get_available_name(test_file_name, timestamp, self.user)
        if not os.path.isdir(app.UPLOAD_FOLDER):
            os.mkdir(app.UPLOAD_FOLDER)
        if not os.path.isdir(self.user.upload_directory()):
            os.mkdir(self.user.upload_directory())
        with open(os.path.join(self.user.upload_directory(), avail_filename), 'w') as file:
            file.write('This is for a test.')
        filehandling.store_additional_data(
            avail_filename,
            {'t': timestamp, 'n': test_file_name, 'nonce1': 123, 'nonce2': 456},
            self.user)
        filehandling.mark_file_as_live(test_file_name, self.user)


    def test_only_live_files_are_listed_as_such(self):
        for i in range(100):
            self.create_test_file("ABC"+str(i)+".cio", 1.0)
        files_listed_uniquely = list(np.array(filehandling.list_live_files(self.user))[:, 0])
        self.assertTrue(len(files_listed_uniquely) == 100, "Expect 100 files to have been created.")
        filehandling.archive_file("ABC69.cio", self.user)
        filehandling.archive_file("ABC33.cio", self.user)
        filehandling.archive_file("ABC42.cio", self.user)
        files_listed_uniquely_without_a_few_files = list(np.array(filehandling.list_live_files(self.user))[:, 0])
        self.assertTrue(len(files_listed_uniquely_without_a_few_files) == 97,
                        "Expect 100 files to have been created of which 3 have been archived.")
        self.assertFalse(files_listed_uniquely == files_listed_uniquely_without_a_few_files,
                         'Expected a few files to have been archived.')
        for name in files_listed_uniquely_without_a_few_files:
            self.assertTrue(name in files_listed_uniquely)
        self.assertTrue(len(files_listed_uniquely_without_a_few_files) + 3 == len(files_listed_uniquely),
                        "Expect three files to be unlisted.")
        for name in files_listed_uniquely:
            if name in ["ABC69.cio", "ABC42.cio", "ABC33.cio"]:
                self.assertFalse(name in files_listed_uniquely_without_a_few_files)
            else:
                self.assertTrue(name in files_listed_uniquely_without_a_few_files)

    def test_archived_files_can_be_resurrected(self):
        self.create_test_file('ABC.cio', 1.0)
        self.create_test_file('ABC1.cio', 1.0)
        self.create_test_file('ABC2.cio', 1.0)
        live_files = list(np.array(filehandling.list_live_files(user=self.user))[:, 0])
        self.assertTrue(len(live_files) == 3)
        filehandling.archive_file('ABC.cio', self.user)
        filehandling.archive_file('ABC1.cio', self.user)
        live_files_with_some_archived = list(np.array(filehandling.list_live_files(self.user))[:, 0])
        self.assertTrue(len(live_files_with_some_archived) == 1 and live_files_with_some_archived == ["ABC2.cio"])
        filehandling.resurrect_file("ABC.cio", self.user)
        filehandling.resurrect_file("ABC1.cio", self.user)
        live_files_with_some_resurrected = list(np.array(filehandling.list_live_files(self.user))[:, 0])
        self.assertTrue(len(live_files_with_some_resurrected) == 3)
        for name in live_files:
            self.assertTrue(name in live_files_with_some_resurrected)

    def test_latest_timestamp_is_the_latest_timestamp(self):
        self.create_test_file('ABC.cio', 1234.5678)
        self.assertTrue(1234.5678 == filehandling.load_latest_timestamp('ABC.cio', self.user),
                        "Time logged was not correct.")


class TestUserHandling(unittest.TestCase):
    def setUp(self) -> None:
        if not os.path.isfile(userhandling.USER_CATALOG):
            self.user_catalog = None
        else:
            with open(userhandling.USER_CATALOG) as catalog:
                self.user_catalog = json.load(catalog)
            os.remove(userhandling.USER_CATALOG)

    def tearDown(self) -> None:
        if os.path.isfile(userhandling.USER_CATALOG):
            os.remove(userhandling.USER_CATALOG)
        if self.user_catalog is None:
            pass  # it already doesn't exist.
        else:
            if not os.path.isdir(app.ADMIN_FOLDER):
                os.mkdir(app.ADMIN_FOLDER)
            with open(userhandling.USER_CATALOG, 'w') as catalog:
                json.dump(self.user_catalog, catalog)

    def test_user_exists_once_registered(self):
        user = userhandling.UserMethodPack("aaaaabbbbbccccc")
        self.assertFalse(user.exists(), "User shouldn't be registered.")
        user.register()
        self.assertTrue(user.exists(), "User should now be registered.")


def create_test_folders():
    if not os.path.exists(app.ADMIN_FOLDER):  # Create the test folder
        os.mkdir(app.ADMIN_FOLDER)
    if os.path.isfile(app.USER_CATALOG):
        os.remove(app.USER_CATALOG)
    if not os.path.exists(app.UPLOAD_FOLDER):  # Create the test folder
        os.mkdir(app.UPLOAD_FOLDER)


def clean_admin_test_folder():
    files_in_testfolder = os.listdir('TEST_ADMIN')
    if 0 != len(files_in_testfolder):
        for filename in files_in_testfolder:
            os.remove(os.path.join('TEST_ADMIN', filename))


def clean_test_folder():
    files_in_testfolder = os.listdir('TEST_FOLDER')
    if 0 != len(files_in_testfolder):
        for filename in files_in_testfolder:
            os.remove(os.path.join('TEST_FOLDER', filename))