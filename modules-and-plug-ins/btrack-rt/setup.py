import os
import os.path
from setuptools import setup


os.environ['BTRACK_SRC'] = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'src'
    )
)


setup(
    name='btrack-rt',
    version="0.1",
    short_description="Real-time beat tracking using BTrack and portaudio",
    author="Daniel Pope",
    author_email="mauve@mauveweb.co.uk",
    cffi_modules=["btrack_build.py:ffibuilder"],
    py_modules=['btrack'],
    install_requires=[
        'cffi>=1.11',
    ]
)
