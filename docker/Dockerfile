# See the ci/ directory for example usage.

ARG PYTHON_VERSION
FROM python:$PYTHON_VERSION-slim-stretch

COPY . /src

RUN apt-get -yqq update && \
    apt-get install -yq --no-install-recommends aria2 && \
    pip install /src && \
    kvm48 --version

ENTRYPOINT ["kvm48"]
CMD        ["--help"]
