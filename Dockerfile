FROM ubuntu:focal

WORKDIR /app

ENV TERM=xterm-256color

# hadolint ignore=DL3008,DL4006
RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-apt \
        python3-venv \
        make \
    && rm -rf /var/lib/apt/lists/* \
    && echo "resolvconf resolvconf/linkify-resolvconf boolean false" \
        | debconf-set-selections

COPY Makefile requirements.txt requirements.yml ./

RUN make install

COPY . ./

RUN make test
