#-*- coding: utf-8 -*-

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
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA  02110-1301 USA.
#
# pylint: disable=C0103,R0904,R0913
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit tests for bugzilla bug handling
'''

import os.path
import re
import sys

import unittest2 as unittest

import srcpath                                   # pylint: disable=W0611
from FedoraReview.name_bug import NameBug
from FedoraReview.spec_file import SpecFile

from FedoraReview import Mock, Settings

from fr_testcase import FR_TestCase


class TestRegressions(FR_TestCase):
    ''' Test some regressions. '''

    def setUp(self):
        FR_TestCase.setUp(self)
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        self.spec_file = os.path.join(os.path.abspath('.'),
                                      'test_regressions',
                                      'test_107_1.spec')
        self.srpm_file = os.path.join(os.path.abspath('.'),
                                      'test_regressions',
                                      'test_107_1-1.0-1.fc17.src.rpm')
        Mock.reset()

    def test_107_changelog_skipping(self):
        """ Test the case when sourceX is name and we use f-r -n so
        that file gets mixed up with a directory
        """
        self.init_test('test_regressions',
                       argv=['-rn', self.srpm_file])
        spec = SpecFile(self.spec_file)
        regex = re.compile('initial fedora')
        self.assertEqual(len(spec.find_all_re(regex)), 2)
        self.assertEqual(len(spec.find_all_re(regex, True)), 1)

    def test_107_no_space_config(self):
        """ Test the case when there is no space in %config line between
        the file and macro itself
        """
        self.init_test('test_regressions',
                       argv=['-rn', self.srpm_file, '--cache'])
        bug = NameBug(self.srpm_file)
        check = self.run_single_check(bug, 'CheckNoConfigInUsr')
        self.assertTrue(check.is_failed)

    def test_107_source_same_as_name(self):
        """ Test the case when Source is equal to %{name}
        """
        srpm_file = os.path.join(os.path.abspath('.'),
                                      'test_regressions',
                                      'test_107_2-1.0-1.fc17.src.rpm')
        self.init_test('test_regressions',
                       argv=['-rn', srpm_file, '--cache'])
        bug = NameBug(srpm_file)
        bug.find_urls()
        self.assertNotEqual(None, bug.srpm_file)
        self.assertNotEqual(None, bug.spec_file)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestRegressions(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRegressions)
    unittest.TextTestRunner(verbosity=2).run(suite)

# vim: set expandtab ts=4 sw=4:
