# Profiling sidecar for WT-7264: perf + gdb + elfutils (eu-stack) + FlameGraph.
# Built for whatever architecture the Docker daemon runs (arm64 or x86-64).
# BASE can be overridden, e.g. --build-arg BASE=public.ecr.aws/docker/library/debian:bookworm-slim
# when Docker Hub rate-limits anonymous pulls.
ARG BASE=debian:bookworm-slim
FROM ${BASE}

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      linux-perf gdb elfutils binutils procps psmisc python3 perl git ca-certificates file curl xz-utils \
 && rm -rf /var/lib/apt/lists/*

# Debian names the binary perf_<kernel-major.minor> and ships a /usr/bin/perf wrapper that refuses to
# run on a different kernel (e.g. Docker Desktop's linuxkit kernel). Expose the real binary as `perf`.
RUN real=$(ls /usr/bin/perf_* 2>/dev/null | head -1); \
    if [ -n "$real" ]; then ln -sf "$real" /usr/local/bin/perf; fi; \
    /usr/local/bin/perf --version || perf --version

# FlameGraph scripts, pinned for reproducibility.
ARG FLAMEGRAPH_COMMIT=41fee1f99f9276008b7cd112fca19dc3ea84ac32
RUN git clone https://github.com/brendangregg/FlameGraph /opt/FlameGraph \
 && git -C /opt/FlameGraph checkout -q ${FLAMEGRAPH_COMMIT}

WORKDIR /work
