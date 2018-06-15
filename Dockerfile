FROM ubuntu:17.10

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    ca-certificates curl file \
    build-essential \
    autoconf automake autotools-dev libtool xutils-dev && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get -y install postgresql-9.6 postgresql-client-9.6 postgresql-contrib-9.6 curl

ENV SSL_VERSION=1.0.2o

RUN curl https://www.openssl.org/source/openssl-$SSL_VERSION.tar.gz -O && \
    tar -xzf openssl-$SSL_VERSION.tar.gz && \
    cd openssl-$SSL_VERSION && ./config && make depend && make install && \
    cd .. && rm -rf openssl-$SSL_VERSION*

ENV OPENSSL_LIB_DIR=/usr/local/ssl/lib \
    OPENSSL_INCLUDE_DIR=/usr/local/ssl/include \
    OPENSSL_STATIC=1

# install all 3 toolchains
RUN curl https://sh.rustup.rs -sSf | \
    sh -s -- --default-toolchain stable -y 

ENV PATH=/root/.cargo/bin:$PATH

# Creating a directory to work from
RUN mkdir -p /usr/src/app

# Copy our app into that directory
COPY . /usr/src/app 
WORKDIR /usr/src/app/rust-play

# Build our app
RUN cargo build
CMD ["cargo", "build"]
CMD ["cargo", "run"]