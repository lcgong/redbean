import setuptools
import setuptools.command.test


class PyTest(setuptools.command.test.test):
    test_package_name = 'MyMainPackage'

    def finalize_options(self):
        self.finalize_options(self)
        _test_args = [
            '--verbose',
            '--ignore=build',
            '--cov=domainics',
            '--cov-report=term-missing',
            # '--pep8',
        ]

        import os
        extra_args = os.environ.get('PYTEST_EXTRA_ARGS')
        if extra_args is not None:
            _test_args.extend(extra_args.split())
        self.test_args = _test_args
        self.test_suite = True

    def run_tests(self):
        import pytest
        from pkg_resources import normalize_path, _namespace_packages

        errno = pytest.main(self.test_args)

        import sys
        sys.exit(errno)


setuptools.setup(
    name='redbean',
    version='0.6.3',
    license="BSD",
    description='A tiny web framwork',
    author='Chenggong Lyu',
    author_email='lcgong@gmail.com',
    url='https://github.com/lcgong/redbean',
    packages=setuptools.find_packages("."),
    # package_dir = {"": "."},
    zip_safe=False,
    install_requires=[
        "aiohttp>=3.7",
        "toml>=0.10",
        "cryptography>=3.3",
        "aiohttp_devtools",
        "pytest",
        "autopep8",
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Utilities",
    ],
    test_suite='test',
    tests_require=[
        'pytest',
        'pytest-pep8',
        'pytest-cov',
    ],
    cmdclass={'test': PyTest},
)
