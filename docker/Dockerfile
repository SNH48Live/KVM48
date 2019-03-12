# See the ci/ directory for example usage.

ARG PYTHON_VERSION
FROM python:$PYTHON_VERSION-slim-stretch

COPY . /src

RUN apt-get -yqq update && \
    apt-get install -yq --no-install-recommends aria2 build-essential wget xz-utils && \
    pip install --pre caterpillar-hls && \
    pip install /src && \
    kvm48 --version

# Download and install a static build of the latest stable release of FFmpeg.
# Because asking Debian to provide a release branch that's less than two years
# old is a stretch (pun intended).
RUN wget --progress=dot:mega -O ffmpeg-static.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg-static.tar.xz --strip-components=1 --wildcards --no-anchored -C /usr/bin ffmpeg && \
    rm ffmpeg-static.tar.xz

ENTRYPOINT ["kvm48"]
CMD        ["--help"]
