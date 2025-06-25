# The devcontainer should use the developer target and run as root with podman
# or docker with user namespaces.
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION} AS developer

# Add any system dependencies for the developer/build environment here
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /virtac
COPY . /virtac/

# Set up a virtual environment and put it in PATH
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
RUN pip install .

ENV EPICS_CA_SERVER_PORT=8064
ENV EPICS_CA_REPEATER_PORT=8065

ENTRYPOINT [ "virtac" ]
CMD ["-v"]
