FROM quay.io/pypa/manylinux2010_x86_64
COPY entrypoint.py /entrypoint.py
RUN /opt/python/cp37-cp37m/bin/pip install twine
RUN yum install -y portaudio-devel fftw-devel libsamplerate-devel
ENTRYPOINT ["/opt/python/cp37-cp37m/bin/python", "/entrypoint.py"]
