#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Checkm class library docs TODO


                [@]SourceFileOrURL  Alg     Digest  Length   ModTime   TargetFileOrURL
TOKEN NUMBER:    1                  2       3       4        5         6

"""

from __future__ import with_statement

COLUMNS = { 0:"SourceFileOrURL",
            1:"Alg",
            2:"Digest",
            3:"Length",
            4:"ModTime",
            5:"TargetFileOrURL",
            }


import os, sys
from stat import *

import re

from collections import defaultdict

import hashlib

import codecs

import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('checkm')

class DirectoryNotFound(Exception):
    """The directory was not found, or is not accessible."""
    def __init__(self, *arg, **kw):
        self.context = (arg, kw)
    def __repr__(self):
        return self.context.__str__()
        
class CheckFailed(Exception):
    """The directory was not found, or is not accessible."""
    def __init__(self, *arg, **kw):
        self.context = (arg, kw)
    def __repr__(self):
        return self.context.__str__()

class CheckmReporter(object):
    COLUMN_NAMES = [u'# [@]SourceFileOrURL',u'Alg',u'Digest',u'Length',u'ModTime']
    def __init__(self):
        self.scanner = CheckmScanner()

    def _get_max_len(self, report):
        cols = defaultdict(lambda : 0)
        for line in report:
            for index in xrange(len(line)):
                if len(line[index])>cols[index]:
                    cols[index] = len(line[index])
        return cols

    def _space_line(self, line, col_maxes):
        spaced_line = []
        for index in xrange(len(line)):
            spaced_line.append(line[index])
            spaces = col_maxes[index]-len(line[index])+4
            spaced_line.append(u" "*spaces)
        return u"".join(spaced_line)

    def create_checkm_file(self, scan_directory, algorithm, checkm_filename, recursive=False, columns=3):
        logger.info("Creating checkm file(%s) for dir(%s) with Alg:%s and columns: %s" % (checkm_filename,
                                                                                          scan_directory,
                                                                                          algorithm, columns))
        report = self.scanner.scan_directory(scan_directory, algorithm, recursive=recursive, columns=columns)
        col_maxes = self._get_max_len(report)
        if hasattr(checkm_filename, 'write'):
            checkm_filename.write("%s \n" % (self._space_line(CheckmReporter.COLUMN_NAMES[:columns], col_maxes)))
            for line in report:
                checkm_filename.write("%s\n" % (self._space_line(line, col_maxes)))
            checkm_filename.write("\n")
            return checkm_filename
        else:
            with codecs.open(checkm_filename, encoding='utf-8', mode="w") as output:
                output.write("%s \n" % (self._space_line(CheckmReporter.COLUMN_NAMES[:columns], col_maxes)))
                for line in report:
                    output.write("%s\n" % (self._space_line(line, col_maxes)))
                output.write("\n")

    def check_checkm_hashes(self, scan_directory, checkm_filename):
        logger.info("Checking files against %s checkm manifest" % checkm_filename)
        parser = CheckmParser(checkm_filename)
        scanner = CheckmScanner()
        for row in parser:
            scan_row = scanner.scan_path(row[0], row[1], len(row))
            if row != scan_row:
                logger.info("Failed original: %s" % row)
                logger.info("Current scan: %s" % scan_row)
                raise CheckFailed(original=row, scan_result=scan_row)

class CheckmParser(object):
    def __init__(self, checkm_file=None):
        self.status = False
        self.lines = []
        if checkm_file:
            self.parse(checkm_file)
    
    def __iter__(self):
        class Checkm_iter:
            def __init__(self, lines):
                self.lines = lines
                self.last = 0
            def __iter__(self):
                return self
            def next(self):
                if self.last >= len(self.lines):         # threshhold terminator
                    raise StopIteration
                elif len(self.lines) == 0:
                    raise StopIteration
                else:
                    self.last += 1
                    return self.lines[self.last-1]
        return Checkm_iter(self.lines)

    def parse(self, checkm_file):
        if not hasattr(checkm_file, "readline"):
            with codecs.open(checkm_file, encoding='utf-8', mode="r") as check_fh:
                self._parse_lines(check_fh)
        else:
            self._parse_lines(checkm_file)

    def _parse_lines(self, fh):
        self.lines = [] # clear the deck
        line_buffer = ""
        def _parse_line(line):
            if not line.startswith('#'):
                tokens = filter(lambda x: x, re.split("\s+", line, 5)) # 6 column max defn == 5 splits
                logger.info(tokens)
                if tokens:
                    #self.lines.append(dict([(index, tokens[index]) for index in xrange(len(tokens))]))
                    self.lines.append(tokens)

        for chunk in fh.read(0x1000):
            line_buffer = line_buffer + chunk
            while True:
                if not line_buffer:
                    break
                fragments = line_buffer.split('\n',1)
                if len(fragments) == 1:
                    break
                _parse_line(fragments[0])
                line_buffer = fragments[1]

class CheckmScanner(object):
    HASHTYPES = ['md5', 'sha1', 'sha224','sha256','sha384','sha512']
    def scan_local(self, directory_path, algorithm, columns=3):
        report = []
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            report.append(self.scan_path(item_path, algorithm, columns))
        return report

    def scan_tree(self, directory_path, algorithm, columns):
        report = []
        if os.path.exists(directory_path):
            for (dirpath, dirnames, filenames) in os.walk(directory_path):
                for item_path in [os.path.join(dirpath, x) for x in dirnames+filenames]:
                    report.append(self.scan_path(item_path, algorithm, columns))
            return report
        else:
            raise DirectoryNotFound(directory_path=directory_path, recursive=recursive)

    def scan_path(self, item_path, algorithm, columns):
        if columns<3 or not isinstance(columns, int):
            columns = 3
        try:
            line = []
            # col 1
            line.append(unicode(item_path))
            # col 2
            line.append(unicode(algorithm))
            # col 3
            if os.path.isdir(item_path):
                line.append(u'd')
            else:
                # No need to catch the ValueError from
                hash_gen = getattr(hashlib, algorithm)()
                with open(item_path, 'rb') as fh:
                    logger.info("Checking %s with algorithm %s" % (item_path, algorithm))
                    chunk = fh.read(1024*8)
                    while chunk:
                        hash_gen.update(chunk)
                        chunk= fh.read(1024*8)
                line.append(unicode(hash_gen.hexdigest()))
            if columns>3:
                # col4 - Length
                line.append(unicode(os.stat(item_path)[ST_SIZE]))
                if columns>4:
                    # col 5 - ModTime
                    line.append(unicode(os.stat(item_path)[ST_MTIME]))
            return line
        except OSError:
            raise DirectoryNotFound(directory_path=directory_path, recursive=recursive)
        except AttributeError:
            raise ValueError("This tool cannot perform hashtype %s" % algorithm)
        
    def scan_directory(self, directory_path, algorithm, recursive=False, columns=3):
        if os.path.exists(directory_path):
            if recursive:
                return self.scan_tree(directory_path, algorithm, columns)
            return self.scan_local(directory_path, algorithm, columns)
        else:
            raise DirectoryNotFound(directory_path=directory_path, recursive=recursive)
