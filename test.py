import os
import random
import string
import unittest


import app

test_folder = 'TEST_FOLDER'


class TestFileNaming(unittest.TestCase):
    def setUp(self):
        app.UPLOAD_FOLDER = 'TEST_FOLDER'  # Change upload folder for the test
        if not os.path.exists(app.UPLOAD_FOLDER):  # Create the test folder
            os.mkdir(app.UPLOAD_FOLDER)
        self.clean_test_folder()

    def test_accepts_acceptable_names(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.cio'
            self.assertTrue(app.acceptable_filename(s))

    def test_rejects_unacceptable_file_ext(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.'
            ext = ''.join(random.choices(string.ascii_lowercase))
            if ext == 'cio':
                continue
            s += ext
            self.assertFalse(app.acceptable_filename(s))

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
            self.assertFalse(app.acceptable_filename(s))

    def test_filenames_converted_to_server_side_name_can_be_converted_back(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.cio'
            ssn = app.filename_to_server_side_name(s)
            s_ = app.server_side_name_to_filename(ssn)
            self.assertTrue(s == s_, s + " != " + s_+ " where ssn = " + ssn)

    def test_list_files_gets_list_of_unique_file(self):
        self.assertTrue(os.path.isdir(test_folder), "expect 'TEST_FOLDER' to be a dir.")
        # Create a bunch of files with random names
        for i in range(10):
            self.create_test_file('test' + str(i) + '_123.123.cio')
            self.create_test_file('test' + str(i) + '_1234.123.cio')
            self.create_test_file('test' + str(i) + '_12345.121.cio')
            self.create_test_file('test' + str(i) + '_12345.123.cio')
            self.create_test_file('test' + str(i) + '_12345.12345.cio')
        # get the actual names of the files.
        filenames_in_dir = os.listdir(test_folder)
        self.assertTrue(len(filenames_in_dir) == 50)
        files_listed_uniquely = app.get_filenames_from_serversidenames_stored()
        self.check_server_side_names_are_listed_uniquely(files_listed_uniquely, filenames_in_dir)

    def check_server_side_names_are_listed_uniquely(self, files_listed_uniquely, filenames_in_dir):
        file_names_seen = []
        for file_named in filenames_in_dir:
            self.assertTrue(app.server_side_name_to_filename(file_named) in files_listed_uniquely,
                            "Expected " + file_named
                            + " to be in file_list as "
                            + app.server_side_name_to_filename(file_named))
            self.assertFalse(file_named in file_names_seen)
            file_names_seen.append(file_named)

    def test_get_latest_gets_latest(self):
        self.assertTrue(os.path.isdir(test_folder), "expect 'TEST_FOLDER' to be a dir.")
        self.create_test_file('test_123.123.cio')
        self.create_test_file('test_1234.123.cio')
        self.create_test_file('test_12345.121.cio')
        self.create_test_file('test_12345.123.cio')
        self.create_test_file('test_12344.125.cio')
        self.assertTrue(app.latest_filename_version('test.cio') == 'test_12345.123.cio')

    # def test_can_save_file(self):  # TODO: Write this test.

    def test_new_files_are_listed_uniquely(self):
        self.assertTrue(os.path.isdir('TEST_FOLDER'), "expect 'TEST_FOLDER' to be a dir.")
        for i in range(100):
            self.create_test_file('test' + str(i) + '_123.123.cio')
        files_listed_uniquely = app.get_filenames_from_serversidenames_stored()
        self.create_test_file('example_123.123.cio')
        files_listed_uniquely_with_new_file = app.get_filenames_from_serversidenames_stored()
        self.assertFalse(files_listed_uniquely == files_listed_uniquely_with_new_file,
                         'Expected new file to have been added.')
        for name in files_listed_uniquely_with_new_file:
            self.assertTrue(name in files_listed_uniquely or name == 'example.cio',
                            'Expect ' + name + ' in previous listing or to be the newly added.')

    def create_test_file(self, test_file_name):
        with open(os.path.join(test_folder, test_file_name), 'w') as file:
            file.write('This is for a test.')

    def clean_test_folder(self):
        files_in_testfolder = os.listdir('TEST_FOLDER')
        if 0 != len(files_in_testfolder):
            for filename in files_in_testfolder:
                os.remove(os.path.join('TEST_FOLDER', filename))

    def test_can_rename_files(self):
        self.assertTrue(os.path.isdir('TEST_FOLDER'), "expect 'TEST_FOLDER' to be a dir.")
        pre_rename_name = 'testbefore_123.123.cio'
        post_rename_name = '123.cio'  # has to be safe
        self.create_test_file(pre_rename_name)
        filenames_in_dir = os.listdir('TEST_FOLDER')
        self.assertTrue(len(filenames_in_dir) == 1)
        self.assertTrue(pre_rename_name in filenames_in_dir)
        app.rename_file(pre_rename_name, post_rename_name)
        filenames_in_dir = os.listdir('TEST_FOLDER')
        self.assertTrue(len(filenames_in_dir) == 1)
        self.assertTrue(app.server_side_name_to_filename(filenames_in_dir[0]) == post_rename_name)


class TestLoginProcedure(unittest.TestCase):
    def setUp(self):
        app.ADMIN_FOLDER = 'TEST_ADMIN'  # Change admin folder for the test
        app.USER_CATALOG = os.path.join(app.ADMIN_FOLDER, 'USERS.txt')
        app.USER_RECENT_CHALLENGES = os.path.join(app.ADMIN_FOLDER, 'CHALLENGES.txt')
        if not os.path.exists(app.ADMIN_FOLDER):  # Create the test folder
            os.mkdir(app.ADMIN_FOLDER)
        if os.path.isfile(app.USER_CATALOG):
            os.remove(app.USER_CATALOG)
        self.clean_admin_folder()

    def test_can_create_user(self):
        self.assertTrue(len(app.get_users()) == 0)  # There should be none.
        app.create_user('ABCD', '12345')
        self.assertTrue(len(app.get_users()) == 1)  # Now we have created one.
        app.create_user('ABCDE', '12345')
        self.assertTrue(len(app.get_users()) == 2)  # Now we have created two.

    def test_cannot_create_one_of_same_identifier(self):
        self.assertTrue(len(app.get_users()) == 0)  # There should be none.
        app.create_user('ABCD', '12345')
        self.assertTrue(len(app.get_users()) == 1)  # Now we have created one.
        app.create_user('ABCD', '67890')
        self.assertTrue(len(app.get_users()) == 1)  # We still have just one.
        self.assertTrue(['ABCD', '12345'] in app.get_users(), '' + str(app.get_users()))

    def test_can_login(self):
        assert False  # Challenge mode not determined yet.
        app.create_user('ABC', '12345')
        challenge = app.issue_challenge('ABC')
        self.assertTrue(app.get_latest_challenge('ABC') == challenge)
        # challenge_response = ???

    def clean_admin_folder(self):
        files_in_testfolder = os.listdir('TEST_ADMIN')
        if 0 != len(files_in_testfolder):
            for filename in files_in_testfolder:
                os.remove(os.path.join('TEST_ADMIN', filename))
