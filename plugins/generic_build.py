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
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>


'''
Test setup: build, install, run rpmlint and install sources.

This is a a sequence of tests which builds, install runs
rpmlint and finally re-install the sources using rpmbuild -bp.
It offers the standard dependency CheckBuildCompleted, which other
tests by default depends on.
'''

import glob
import os
import os.path

# pylint: disable=W0611
try:
    from subprocess import check_output
except ImportError:
    from FedoraReview.el_compat import check_output
# pylint: enable=W0611


import FedoraReview.deps as deps
from FedoraReview import CheckBase, Mock, ReviewDirs, Settings
from FedoraReview import RegistryBase, ReviewError


class Registry(RegistryBase):
    ''' Module registration, register all checks in group Setup. '''

    group = 'Generic.build'

    def is_applicable(self):
        return self.checks.groups['Generic'].is_applicable()


class BuildCheckBase(CheckBase):
    ''' Base class for all generic tests. '''

    sort_key = '10'

    def __init__(self, checks):
        CheckBase.__init__(self, checks, __file__)
        self.rpmlint_output = []

    def run_rpmlint(self, filenames):
        """ Runs rpmlint against the provided files.

        arg: filenames, list of filenames  to run rpmlint on
        """
        cmd = 'rpmlint -f .rpmlint ' + ' '.join(filenames)
        out = 'Checking: '
        sep = '\n' + ' ' * len(out)
        out += sep.join([os.path.basename(f) for f in filenames])
        out += '\n'
        out += self._run_cmd(cmd)
        out += '\n'
        with open('rpmlint.txt', 'w') as f:
            f.write(out)
        for line in out.split('\n'):
            if line and len(line) > 0:
                self.rpmlint_output.append(line)
        no_errors, msg  = self.check_rpmlint_errors(out, self.log)
        return no_errors, msg if msg else out

    def rpmlint(self):
        """ Runs rpmlint against the file.
        """
        return self.run_rpmlint([self.filename])

    def rpmlint_rpms(self):
        """ Runs rpmlint against the used rpms - prebuilt or built in mock.
        """
        rpms = Mock.get_package_rpm_paths(self.spec)
        no_errors, result = self.run_rpmlint(rpms)
        return no_errors, result + '\n'


def _mock_root_setup(while_what):
    ''' Wrap mock --init. '''

    class DependencyInstallError(ReviewError):
        ''' Raised when a package in local repo can't be installed. '''
        pass

    Mock.init()
    if Settings.repo:
        repodir = Settings.repo
        if not repodir.startswith('/'):
            repodir = os.path.join(ReviewDirs.startdir, repodir)
        rpms = glob.glob(os.path.join(repodir, '*.rpm'))
        error = Mock.install(rpms)
        if error:
            raise DependencyInstallError(while_what + ': ' + error)


class CheckResultdir(BuildCheckBase):
    '''
    EXTRA: The resultdir must be empty, since we later on will assume
    anything there is generated by mock.
    '''

    class NotEmptyError(ReviewError):
        ''' The resultdir is not empty. '''
        def __init__(self):
            ReviewError.__init__(self, "The result dir is not empty")
            self.show_logs = False

    def __init__(self, base):
        BuildCheckBase.__init__(self, base)
        self.automatic = True
        self.needs = []
        self.text = 'Resultdir need to be empty before review'

    def run(self):
        if len(glob.glob(os.path.join(Mock.resultdir, '*.*'))) != 0 \
            and not (Settings.nobuild or Settings.prebuilt):
                raise self.NotEmptyError()       # pylint: disable=W0311
        self.set_passed(self.NA)


class CheckBuild(BuildCheckBase):
    '''
    MUST: The package MUST successfully compile and build into binary
    rpms on at least one primary architecture.
    '''

    def __init__(self, base):
        BuildCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Architecture_Support'
        self.text = 'Package successfully compiles and builds into' \
                    ' binary rpms on at least one supported primary' \
                    ' architecture.'
        self.automatic = True
        self.needs = ['CheckResultdir']

    def run(self):

        def listfiles():
            ''' Generate listing of dirs and files in each package. '''
            with open('files.dir', 'w') as f:
                for pkg in self.spec.packages:
                    path = Mock.get_package_rpm_path(pkg, self.spec)
                    dirs, files = deps.listpaths(path)
                    f.write(pkg + '\n')
                    f.write('=' * len(pkg) + '\n')
                    for line in sorted(dirs):
                        f.write(line + '\n')
                    f.write('\n')
                    for line in sorted(files):
                        f.write(line + '\n')
                    f.write('\n')

        if Settings.prebuilt:
            self.set_passed(self.PENDING, 'Using prebuilt packages')
            listfiles()
            return
        if Settings.nobuild:
            if Mock.have_cache_for(self.spec):
                self.set_passed(self.PENDING,
                                'Re-using old build in mock')
                return
            else:
                self.log.info(
                        'No valid cache, building despite --no-build.')
        _mock_root_setup("While building")
        Mock.build(self.srpm.filename)
        listfiles()
        self.set_passed(self.PASS)


class CheckRpmlint(BuildCheckBase):
    '''
    MUST: rpmlint must be run on the source rpm and all binary rpms
    the build produces.  The output should be posted in the review.
    '''
    def __init__(self, base):
        BuildCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#rpmlint'
        self.text = 'Rpmlint is run on all rpms the build produces.'
        self.automatic = True
        self.type = 'MUST'
        self.needs = ['CheckBuild']

    def run(self):
        if not self.checks.checkdict['CheckBuild'].is_failed:
            no_errors, retval = self.rpmlint_rpms()
            text = 'No rpmlint messages.' if no_errors else \
                        'There are rpmlint messages (see attachment).'
            attachments = [self.Attachment('Rpmlint', retval, 5)]
            self.set_passed(self.PASS, text, attachments)
        else:
            self.set_passed(self.FAIL, 'Mock build failed')


class CheckPackageInstalls(BuildCheckBase):
    ''' Install package in mock. '''

    def __init__(self, base):
        BuildCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package installs properly.'
        self.automatic = True
        self.type = 'MUST'
        self.needs = ['CheckRpmlint']

    def check_build_installed(self):
        ''' Return list of used rpms which are not installed'''
        bad_ones = []
        for pkg in self.spec.packages:
            try:
                Mock.get_package_rpm_path(pkg, self.spec)
            except ReviewError:
                bad_ones.append(pkg)
        return bad_ones

    def run(self):
        if Settings.nobuild:
            bad_ones = self.check_build_installed()
            if bad_ones == []:
                self.set_passed(self.PASS)
            else:
                bad_ones = list(set(bad_ones))
                self.set_passed(self.FAIL,
                                '--no-build: package(s) not installed')
                self.log.info('Packages required by --no-build are'
                              ' not installed: ' + ', '.join(bad_ones))
            return
        _mock_root_setup('While installing built packages')
        rpms = Mock.get_package_rpm_paths(self.spec)
        self.log.info('Installing built package(s)')
        output = Mock.install(rpms)
        if not output:
            self.set_passed(self.PASS)
        else:
            attachments = [
                self.Attachment('Installation errors', output, 3)]
            self.set_passed(self.FAIL,
                           "Installation errors (see attachment)",
                            attachments)


class CheckRpmlintInstalled(BuildCheckBase):
    '''
    EXTRA: Not in guidelines, but running rpmlint on the installed
    package occasionally reveals things otherwise not found.
    '''
    def __init__(self, base):
        BuildCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#rpmlint'
        self.text = 'Rpmlint is run on all installed packages.'
        self.automatic = True
        self.type = 'EXTRA'
        self.needs = ['CheckPackageInstalls']

    def run(self):
        if self.checks.checkdict['CheckPackageInstalls'].is_passed:
            rpms = Mock.get_package_rpm_paths(self.spec)
            no_errors, retcode = Mock.rpmlint_rpms(rpms)
            text = 'No rpmlint messages.' if no_errors else \
                             'There are rpmlint messages (see attachment).'
            attachments = \
                [self.Attachment('Rpmlint (installed packages)',
                                 retcode + '\n', 5)]
            self.set_passed(self.PASS, text, attachments)
        else:
            self.set_passed(self.FAIL, 'Mock build failed')


class CheckInitDeps(BuildCheckBase):
    ''' EXTRA: Setup the repoquery wrapper.  No output in report '''

    def __init__(self, base):
        BuildCheckBase.__init__(self, base)
        self.automatic = True
        self.type = 'EXTRA'
        self.needs = ['CheckRpmlintInstalled']

    def run(self):
        deps.init()
        self.set_passed(self.NA)


class CheckBuildCompleted(BuildCheckBase):
    '''
    EXTRA: This test is the default dependency. Requiring this test means
    requiring the build, rpmlint and restored source using rpmbuild -bp
    under BUILD. The test runs rpmbuild -bp, but leaves no trace in report.
    '''
    def __init__(self, base):
        BuildCheckBase.__init__(self, base)
        self.url = ''
        self.text = 'This text is never shown'
        self.automatic = True
        self.type = 'EXTRA'
        self.needs = ['CheckInitDeps']

    def run(self):
        Mock.clear_builddir()
        errmsg = Mock.rpmbuild_bp(self.srpm)
        if errmsg:
            self.log.debug(
                "Cannot do rpmbuild -bp, trying with builddeps")
            Mock.install(self.spec.build_requires)
            Mock.rpmbuild_bp(self.srpm)
        if os.path.lexists('BUILD'):
            os.unlink('BUILD')
        os.symlink(Mock.get_builddir('BUILD'), 'BUILD')
        self.set_passed(self.NA)


# vim: set expandtab ts=4 sw=4:
