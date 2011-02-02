#!/usr/bin/python -tt
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit cases for automatic test of fedora review guidelines
'''



import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import os
import os.path
import unittest
from reviewtools import Helpers
from reviewtools.checks import *
from bugzilla import Bugzilla
from base import *

class CheckCaseChecks(unittest.TestCase):
    def __init__(self, methodName='runCheck'):
        unittest.TestCase.__init__(self, methodName)
        self.cases = None
        self.srpm = TEST_WORK_DIR + os.path.basename(TEST_SRPM)
        self.spec = TEST_WORK_DIR + os.path.basename(TEST_SPEC)
        self.source = TEST_WORK_DIR + os.path.basename(TEST_SRC)
        
    def setUp(self):
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        helper = Helpers()
        helper.set_work_dir(TEST_WORK_DIR)
        helper._get_file(TEST_SRPM)
        helper._get_file(TEST_SRC)
        helper._get_file(TEST_SPEC)
        del helper 

    def test_all_checks(self):
        ''' Run all automated review checks'''
        print('Setup Checks')
        self.cases = Checks(self.spec, self.srpm, self.source)
        self.cases.add('name', CheckName)     
        self.cases.add('specname', CheckSpecName)   
        self.cases.add('illegal_tag', CheckIllegalSpecTags)   
        self.cases.add('buildroot', CheckBuildroot)   
        self.cases.add('clean', CheckClean)   
        self.cases.add('install', CheckInstall)   
        self.cases.add('defattr', CheckDefattr)  
        self.cases.add('MD5', CheckSourceMD5)
        self.cases.add('build', CheckBuild)
        self.cases.add('rpmlint', CheckRpmLint)
        print('Running All Checks')
        self.cases.run_tests()   
        for tag in self.cases.taglist:
            test = self.cases.tests[tag]
            result = test.get_result()
            self.assertEqual(result[1:2],'x')
            
