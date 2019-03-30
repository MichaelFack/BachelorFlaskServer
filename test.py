import os
import random
import secrets
import string
import unittest

import app
import filehandling
import userhandling

test_folder = 'TEST_FOLDER'


class TestFileNaming(unittest.TestCase):
    def setUp(self):
        app.UPLOAD_FOLDER = 'TEST_FOLDER'  # Change upload folder for the test
        if not os.path.exists(app.UPLOAD_FOLDER):  # Create the test folder
            os.mkdir(app.UPLOAD_FOLDER)

    def tearDown(self):
        self.clean_test_folder()

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
            ssn = filehandling.filename_to_server_side_name(s)
            s_ = filehandling.server_side_name_to_filename(ssn)
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
        files_listed_uniquely = filehandling.get_filenames_from_serversidenames_stored()
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
        self.assertTrue(os.path.isdir(test_folder), "expect 'TEST_FOLDER' to be a dir.")
        self.create_test_file('test_123.123.cio')
        self.create_test_file('test_1234.123.cio')
        self.create_test_file('test_12345.121.cio')
        self.create_test_file('test_12345.123.cio')
        self.create_test_file('test_12344.125.cio')
        self.assertTrue(filehandling.latest_filename_version('test.cio') == 'test_12345.123.cio')

    # def test_can_save_file(self):  # TODO: Write this test.

    def test_new_files_are_listed_uniquely(self):
        self.assertTrue(os.path.isdir('TEST_FOLDER'), "expect 'TEST_FOLDER' to be a dir.")
        for i in range(100):
            self.create_test_file('test' + str(i) + '_123.123.cio')
        files_listed_uniquely = filehandling.get_filenames_from_serversidenames_stored()
        self.create_test_file('example_123.123.cio')
        files_listed_uniquely_with_new_file = filehandling.get_filenames_from_serversidenames_stored()
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
        filehandling.rename_file(pre_rename_name, post_rename_name)
        filenames_in_dir = os.listdir('TEST_FOLDER')
        self.assertTrue(len(filenames_in_dir) == 1)
        self.assertTrue(filehandling.server_side_name_to_filename(filenames_in_dir[0]) == post_rename_name)


class TestLoginProcedure(unittest.TestCase):
    def setUp(self):
        app.ADMIN_FOLDER = 'TEST_ADMIN'  # Change admin folder for the test
        app.USER_CATALOG = os.path.join(app.ADMIN_FOLDER, 'USERS.txt')
        app.USER_RECENT_CHALLENGES = os.path.join(app.ADMIN_FOLDER, 'CHALLENGES.txt')
        if not os.path.exists(app.ADMIN_FOLDER):  # Create the test folder
            os.mkdir(app.ADMIN_FOLDER)
        if os.path.isfile(app.USER_CATALOG):
            os.remove(app.USER_CATALOG)

    def tearDown(self):
        self.clean_admin_test_folder()

    def test_can_create_user(self):
        self.assertTrue(len(userhandling.get_users()) == 0)  # There should be none.
        userhandling.create_user('ABCD', '12345')
        self.assertTrue(len(userhandling.get_users()) == 1)  # Now we have created one.
        userhandling.create_user('ABCDE', '12345')
        self.assertTrue(len(userhandling.get_users()) == 2)  # Now we have created two.

    def test_cannot_create_two_of_same_identifier(self):
        self.assertTrue(len(userhandling.get_users()) == 0)  # There should be none.
        random_salt = secrets.token_hex(16)
        self.assertTrue(userhandling.create_user('ABCD', random_salt))
        self.assertTrue(len(userhandling.get_users()) == 1)  # Now we have created one.
        self.assertFalse(userhandling.create_user('ABCD', '67890'))
        self.assertTrue(len(userhandling.get_users()) == 1)  # We still have just one.
        self.assertTrue(['ABCD', random_salt] in userhandling.get_users(),
                        '' + str(userhandling.get_users()))

    def test_can_login(self):
        userhandling.create_user('ABC', secrets.token_hex(16))
        challenge = userhandling.issue_challenge('ABC')
        self.assertTrue(userhandling.get_latest_challenge('ABC') == challenge)
        challenge_response = userhandling.compute_challenge_response(challenge, 'ABC')
        self.assertTrue(
            userhandling.validate_challenge_response(
                'ABC',
                challenge_response))

    def test_bad_response_cannot_log_in_while_correct_can(self):
        userhandling.create_user('ABC', secrets.token_hex(16))
        challenge = userhandling.issue_challenge('ABC')
        self.assertTrue(userhandling.get_latest_challenge('ABC') == challenge)
        wrong_response = userhandling.compute_challenge_response(challenge, '')
        challenge_response = userhandling.compute_challenge_response(challenge, 'ABC')
        self.assertFalse(userhandling.validate_challenge_response(
            'ABC', wrong_response
        ), "Name is '' should not validate.")
        for i in range(1000):
            random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(i))
            wrong_response = userhandling.compute_challenge_response(challenge, random_string)
            self.assertFalse(userhandling.validate_challenge_response(
                'ABC', wrong_response
            ), "Response generated from random name should not validate.")
        for i in range(1000):
            random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(i))
            wrong_response = userhandling.compute_challenge_response(challenge, random_string)
            self.assertFalse(userhandling.validate_challenge_response(
                random_string, wrong_response
            ), "Response generated from random name and matching name should not validate.")
        for i in range(1000):
            random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(i))
            if random_string == 'ABC': continue  # Let's be sure we get the name wrong.
            self.assertFalse(userhandling.validate_challenge_response(
                random_string, challenge_response
            ), "Random name with correct response should not validate.")
        self.assertTrue(userhandling.validate_challenge_response(
            'ABC', challenge_response
        ), "Should be able to log in correctly (assuming timeout hasn't occured).")

    def test_cannot_log_in_as_someone_else_with_own_response(self):
        user_id_1 = 'ABC'
        user_id_2 = 'ABCD'
        random_salt = secrets.token_hex(16)
        self.assertTrue(userhandling.create_user(user_id_1, random_salt))
        self.assertTrue(userhandling.create_user(user_id_2, random_salt))
        challenge_1 = userhandling.issue_challenge('ABC')
        challenge_response_1 = userhandling.compute_challenge_response(challenge_1, user_id_1)
        self.assertFalse(userhandling.validate_challenge_response(user_id_2, challenge_response_1))
        challenge_2 = userhandling.issue_challenge(user_id_2)
        self.assertFalse(userhandling.validate_challenge_response(user_id_2, challenge_response_1))

    def clean_admin_test_folder(self):
        files_in_testfolder = os.listdir('TEST_ADMIN')
        if 0 != len(files_in_testfolder):
            for filename in files_in_testfolder:
                os.remove(os.path.join('TEST_ADMIN', filename))
