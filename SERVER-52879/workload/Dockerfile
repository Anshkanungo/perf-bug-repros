# Client-side tools image for SERVER-52879 (dependencies only).
# The scripts themselves (workload/*.py, analysis/*.py) are bind-mounted at run time by run.sh /
# analyze.sh, so editing them never requires a rebuild.
# BASE can be overridden, e.g. --build-arg BASE=public.ecr.aws/docker/library/python:3.12-slim-bookworm
# when Docker Hub rate-limits anonymous pulls.
ARG BASE=python:3.12-slim-bookworm
FROM ${BASE}

# pymongo 4.10 supports MongoDB 3.6 through 8.0, so the same client works against 4.4.x and newer builds.
RUN pip install --no-cache-dir \
      pymongo==4.10.1 \
      numpy==2.1.3 \
      pandas==2.2.3 \
      matplotlib==3.9.2

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
