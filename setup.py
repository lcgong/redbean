import setuptools
import setuptools.command.test


setuptools.setup(
    name='redbean',
    version='0.6.5',
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
        "watchgod>=0.6",
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
)
