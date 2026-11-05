# Environment recipe. First build requires network; no prebuilt image is shipped.
# Ubuntu package revisions follow security updates; record the built image ID.
FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git make build-essential python3 perl autoconf flex bison util-linux \
    help2man ccache zlib1g-dev liblz4-dev libreadline-dev libsdl2-dev libzstd-dev \
    openjdk-21-jdk-headless clang-19 lld-19 llvm-19 \
    gcc-12-riscv64-linux-gnu binutils-riscv64-linux-gnu \
    libc6-dev-riscv64-cross && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH=/opt/mill:/opt/verilator/bin:/usr/lib/llvm-19/bin:/usr/lib/jvm/java-21-openjdk-amd64/bin:${PATH}
RUN mkdir -p /opt/mill && \
    curl -fL --retry 3 https://repo.maven.apache.org/maven2/com/lihaoyi/mill-dist/0.12.3/mill-dist-0.12.3.jar -o /opt/mill/mill.jar && \
    echo '9e2bd55d01428d0e14e93327bcb94e7d6cd0fdc0  /opt/mill/mill.jar' | sha1sum -c - && \
    printf '#!/bin/sh\nexec sh /opt/mill/mill.jar "$@"\n' > /opt/mill/mill && chmod 755 /opt/mill/mill && \
    mill --version
RUN apt-get update && apt-get install -y --no-install-recommends libfl-dev && \
    test -f /usr/include/FlexLexer.h && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch v5.052 https://github.com/verilator/verilator.git /tmp/verilator && \
    cd /tmp/verilator && autoconf && ./configure --prefix=/opt/verilator CC=clang CXX=clang++ && \
    make -j4 && make install && verilator --version && rm -rf /tmp/verilator
RUN apt-get update && apt-get install -y --no-install-recommends time libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/* && dpkg-query -W > /opt/installed-packages.txt
ENV VDOT_RISCV_CC=/usr/bin/riscv64-linux-gnu-gcc-12
ENV COURSIER_REPOSITORIES=https://repo.maven.apache.org/maven2
ENV COURSIER_CACHE=/cache/coursier
ENV XDG_CACHE_HOME=/cache/xdg
WORKDIR /workspace
CMD ["bash"]
