FROM ubuntu:focal

WORKDIR /app

ENV TERM=xterm-256color

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-apt \
        python3-venv \
        make \
    && rm -rf /var/lib/apt/lists/*

COPY . ./

RUN make install \
    && make test
