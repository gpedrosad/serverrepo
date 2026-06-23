FROM --platform=linux/386 i386/ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  g++ \
  make \
  cmake \
  git \
  gdb \
  libxml2-dev \
  liblua5.1-0-dev \
  libboost-regex-dev \
  zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app/YurOTS

CMD ["bash"]
