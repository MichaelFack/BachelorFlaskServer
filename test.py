import random
import string
import unittest

from app import filename_to_server_side_name, server_side_name_to_filename, latest_filename_version, acceptable_file


class TestFilenaming(unittest.TestCase):
    def setUp(self):
        pass

    def test_accepts_acceptable_names(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.cio'
            self.assertTrue(acceptable_file(s))

    def test_rejects_unacceptable_file_ext(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.'
            ext = ''.join(random.choices(string.ascii_lowercase))
            if ext == 'cio':
                continue
            s += ext
            self.assertFalse(acceptable_file(s))

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
            self.assertFalse(acceptable_file(s))

    def test_filenames_converted_to_server_side_name_can_be_converted_back(self):
        for i in range(10000):
            n = random.randint(10, 20)
            s = ''.join(random.choices(string.hexdigits, k=n))
            s += '.cio'
            ssn = filename_to_server_side_name(s)
            s_ = server_side_name_to_filename(ssn)
            self.assertTrue(s == s_, s + " != " + s_+ " where ssn = " + ssn)