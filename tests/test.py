# -*- coding: utf-8 -*-
import random, unittest, re

import os, shutil

from StringIO import StringIO

from tempfile import mkstemp, mkdtemp

import checkm

import logging

import codecs

# C - checkm format
# B - bagit format

EMPTY_C = "# Comments shouldn't be parsed\n"

EMPTY_B = ""

SINGLELINE_C_SIMPLE = "./filename           45aa56b8    md5\n"

SINGLELINE_B_SIMPLE = "767bbc45aa56b8  ./filename\n"

MULTILINE_C_LIST_MANIFEST = """# Just a list of files, not manifest info really
./filenames/in/simple/manifest/format/no/hash
./filenames/in/simple/manifest/format/no/hash
./filenames/in/simple/manifest/format/no/hash
./filenames/in/simple/manifest/format/no/hash
./filenames/in/simple/manifest/format/no/hash
"""

MULTILINE_C_BAR_MANIFEST = """#%checkm_0.7
#%profile http://example.com/profile
./filenames/in/simple/manifest/format | md5 | 3f279a2757668a1b44db7b2c2a4a2f4e | 1 | | 
./filenames/in/simple/manifest/format | md5 | 3f279a2757668a1b44db7b2c2a4a2f4e | 1 | | 
./filenames/in/simple/manifest/format | md5 | 3f279a2757668a1b44db7b2c2a4a2f4e | 1 | | 
./filenames/in/simple/manifest/format | md5 | 3f279a2757668a1b44db7b2c2a4a2f4e | 1 | | 
"""

MULTILINE_B_MANIFEST = """3f279a2757668a1b44db7b2c2a4a2f4e  ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  ./filenames/in/simple/manifest/format
"""

MULTILINE_B_VARSPACING_MANIFEST = """3f279a2757668a1b44db7b2c2a4a2f4e    ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e       ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e      ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e         ./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e    ./filenames/in/simple/manifest/format
"""

MULTILINE_B_STARRED_MANIFEST = """3f279a2757668a1b44db7b2c2a4a2f4e  *./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  *./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  *./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  *./filenames/in/simple/manifest/format
3f279a2757668a1b44db7b2c2a4a2f4e  *./filenames/in/simple/manifest/format
"""
# foo.txt = "12345678901234567890\n"
FOO_TXT_MD5 = "5f67d236ba5ffbed4a5b33df87bacecc"

class TestCheckm(unittest.TestCase):
    def pass_as_file(self, text, func, filename_param=None, **kw):
        (fd, filename) = mkstemp()
        handle = os.fdopen(fd, "w")
        handle.write(text)
        handle.close()
        if not filename_param:
            results = func(filename)
        else:
            kw[filename_param] = filename
            results = func(**kw)
        os.remove(filename)
        return results
        
    def create_toplevel_checkm_bag(self):
        dirname = mkdtemp()
        if self.dirnames:
            self.dirnames.append(dirname)
        else:
            self.dirnames = [dirname]
        for subdir in [['1'],['2'],['3'],['1','1'],['1','2'],['1','3'],['2','data']]:
            os.mkdir(os.path.join(dirname, *subdir))
        checkm_f = open(os.path.join(dirname, "default_checkm.txt"), "wb")
        checkm_f.write("#Meaningless comments\n# Should be ignored!\n")
        for (d,_,_) in os.walk(dirname):
            checkm_f.write("%s md5 d\n" % d)
            output = open(os.path.join(d,'foo.txt'), "wb")
            # write a file that has a known md5sum
            output.write("12345678901234567890\n")
            checkm_f.write("%s md5 %s\n" % (os.path.join(d,'foo.txt'), FOO_TXT_MD5))
        return dirname

    def create_toplevel_checkm_report(self):
        dirname = mkdtemp()
        if self.dirnames:
            self.dirnames.append(dirname)
        else:
            self.dirnames = [dirname]
        for subdir in [['1'],['2'],['3'],['1','1'],['1','2'],['1','3'],['2','data']]:
            os.mkdir(os.path.join(dirname, *subdir))
        for (d,_,_) in os.walk(dirname):
            output = open(os.path.join(d,'foo.txt'), "wb")
            # write a file that has a known md5sum
            output.write("12345678901234567890\n")
        output = codecs.open(os.path.join(dirname, 'default_checkm.txt'), encoding='utf-8', mode="w")
        self.reporter.create_checkm_file(dirname, 'md5', 'default_checkm.txt', False, 3, output)
        return dirname

    def create_multi_checkm_bag(self):
        dirname = mkdtemp()
        if self.dirnames:
            self.dirnames.append(dirname)
        else:
            self.dirnames = [dirname]
        for subdir in [['1'],['2'],['3'],['1','1'],['1','dada'],['1','3'],['1','1','foobar'],['1','3','data']]:
            os.mkdir(os.path.join(dirname, *subdir))
            for (d,subdirs,_) in os.walk(dirname, topdown=False):
                checkm_f = open(os.path.join(d,'m_checkm.txt'), "wb")
                checkm_f.write("# Meaningless comment!\n")
                for subd in subdirs:
                    checkm_f.write("%s md5 d\n" % os.path.join(d,subd))
                    checkm_f.write("@%s md5 -\n" % os.path.join(d,subd, 'm_checkm.txt'))
                output = open(os.path.join(d,'foo.txt'), "wb")
                # write a file that has a known md5sum
                output.write("12345678901234567890\n")
                checkm_f.write("%s md5 %s\n" % (os.path.join(d,'foo.txt'), FOO_TXT_MD5))
        return dirname

    def remove_bag(self, dirname):
        try:
            shutil.rmtree(dirname)
        except:
            pass

    def setUp(self):
        if not hasattr(self, "dirnames"):
            self.dirnames = []
        self.reporter = checkm.CheckmReporter()
        self.scanner = checkm.CheckmScanner()
        self.checkm_p = checkm.CheckmParser()
        self.bagit_p = checkm.BagitParser()
        checkm.logger.setLevel(logging.ERROR)
        
    def tearDown(self):
        for dirname in self.dirnames:
            self.remove_bag(dirname)
        
    def test_empty(self):
        pass

    def test_checkmp_emptyline_fromfilelike(self):
        s = StringIO(EMPTY_C)
        lines = self.checkm_p.parse(s)
        # Empty string should result in an empty list
        self.assertEqual(len(lines), 0)
        self.assertFalse(lines)
        
    def test_checkmp_emptyline_fromfile(self):
        lines = self.pass_as_file(EMPTY_C, self.checkm_p.parse)
        # Empty string should result in an empty list
        self.assertEqual(len(lines), 0)
        self.assertFalse(lines)
        
    def test_checkmp_simpleline_fromfilelike(self):
        s = StringIO(SINGLELINE_C_SIMPLE)
        lines = self.checkm_p.parse(s)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line[0], './filename')
        self.assertEqual(line[1], '45aa56b8')
        self.assertEqual(line[2], 'md5')
        
    def test_checkmp_simpleline_fromfile(self):
        lines = self.pass_as_file(SINGLELINE_C_SIMPLE, self.checkm_p.parse)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line[0], './filename')
        self.assertEqual(line[1], '45aa56b8')
        self.assertEqual(line[2], 'md5')
        
    def test_checkmp_nospaceline_fromfilelike(self):
        # Should 'parse' to 5 lines of 1 element each
        s = StringIO(MULTILINE_C_LIST_MANIFEST)
        lines = self.checkm_p.parse(s)
        self.assertEqual(len(lines), 5)
        self.assertEqual(len(lines[0]), 1)

    def test_checkmp_bar_separated_lines(self):
        # Should parses to 4 lines of 6 elements each
        # The separator '|' should not appear in the list
        s = StringIO(MULTILINE_C_BAR_MANIFEST)
        lines = self.checkm_p.parse(s)
        self.assertEqual(len(lines), 4)
        self.assertEqual(len(lines[0]), 6)
        self.failIfEqual(lines[0][1], '|')

    def test_checkmp_allow_empty_columns(self):
        s = StringIO(MULTILINE_C_BAR_MANIFEST)
        lines = self.checkm_p.parse(s)
        self.assertEqual(len(lines), 4)
        self.assertEqual(len(lines[0]), 6)
        self.assertEqual(lines[0][4], '')

    def test_checkmp_loadsacolumns_fromfilelike(self):
        # Should 'parse' to 5 lines of 1 element each
        s = StringIO("""one two three four five six six_still six_again\n""")
        lines = self.checkm_p.parse(s)
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(lines[0]), 6)
        self.assertEqual(lines[0][5], "six six_still six_again")
        
    def test_checkmp_nospaceline_fromfile(self):
        # Should 'parse' to 5 lines of 1 element each
        lines = self.pass_as_file(MULTILINE_C_LIST_MANIFEST, self.checkm_p.parse)
        self.assertEqual(len(lines), 5)
        self.assertEqual(len(lines[0]), 1)

    def test_checkmp_loadsacolumns_fromfile(self):
        # Should 'parse' to 5 lines of 1 element each
        lines = self.pass_as_file("""one two three four five six six_still six_again\n""", self.checkm_p.parse)
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(lines[0]), 6)
        self.assertEqual(lines[0][5], "six six_still six_again")

    def test_check_checkm(self):
        dirname = self.create_toplevel_checkm_bag()
        checkm_file = os.path.join(dirname, "default_checkm.txt")
        report = self.reporter.check_checkm_hashes(dirname, checkm_file, ignore_multilevel=True)
        self.assertFalse(report['fail'])
        
    def test_check_checkm_multi(self):
        dirname = self.create_multi_checkm_bag()
        checkm_file = os.path.join(dirname, "m_checkm.txt")
        report = self.reporter.check_checkm_hashes(dirname, checkm_file, ignore_multilevel=False)
        self.assertFalse(report['fail'])
        self.assertEqual(len(report['pass']), 25)  # 22 files/dirs to check from that particular bag
        self.assertEqual(len(report['include']), 8) # 7 m_checkm.txt files included

    def test_scanner_produces_nontrivial_file(self):
        dirname = self.create_toplevel_checkm_report()
        checkm_filename = os.path.join(dirname, "default_checkm.txt")
        self.assertTrue(os.path.isfile(checkm_filename))
        self.failIfEqual(0, os.path.getsize(checkm_filename))

    def test_scanner_uses_bars(self):
        dirname = self.create_toplevel_checkm_report()
        checkm_file = open(os.path.join(dirname, "default_checkm.txt"), "r")
        for line in checkm_file:
            if not line.startswith('#'):
                self.failIfEqual(line.find('|'), -1)
                break

    def test_scanner_provides_version_string(self):
        dirname = self.create_toplevel_checkm_report()
        checkm_file = open(os.path.join(dirname, "default_checkm.txt"), "r")
        line = checkm_file.readline()
        self.failIfEqual(None, re.match('^#%checkm_\d+\.\d+\s*$', line))

if __name__ == '__main__':
    unittest.main()
