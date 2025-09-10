ARG UCS_VERSION=5.2.2

FROM gitregistry.knut.univention.de/univention/dev/projects/ucs-base-image/ucs-base-flex:${UCS_VERSION} AS idc-base

ENV PYTHONUNBUFFERED=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PIPX_BIN_DIR="/usr/local/bin"
ENV VIRTUAL_ENV="/venv"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# renovate: datasource=pypi depName=poetry packageName=poetry
ENV POETRY_VERSION=1.8.3

# renovate: datasource=github-releases depName=s6-overlay packageName=just-containers/s6-overlay versioning=loose
ENV S6_OVERLAY_VERSION=v3.1.6.2

RUN python3 -m venv $VIRTUAL_ENV
# Use the venv enabled python
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /ucsschool-id-connector

# Build steps
FROM idc-base as idc-build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    xz-utils \
    pipx \
    && rm -rf /var/lib/apt/lists/*
RUN pipx install poetry=="$POETRY_VERSION"

# Add S6
ADD https://github.com/just-containers/s6-overlay/releases/download/${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN mkdir /s6
RUN tar -C /s6 -Jxpf /tmp/s6-overlay-noarch.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C /s6 -Jxpf /tmp/s6-overlay-x86_64.tar.xz

COPY src/ /ucsschool-id-connector/src/

RUN cd /ucsschool-id-connector/src/ && poetry install --compile --with dev,test
RUN cd /ucsschool-id-connector/src && \
    poetry run rst2html README.rst README.html && \
    poetry run rst2html HISTORY.rst HISTORY.html
RUN cd /ucsschool-id-connector/src/ && poetry install --compile --sync --only main
RUN cd /ucsschool-id-connector/src/ && poetry export --format requirements.txt --with test --output=/ucsschool-id-connector/requirements-test.txt

# install app
FROM idc-base as idc-prod

COPY --from=idc-build $VIRTUAL_ENV $VIRTUAL_ENV
COPY --from=idc-build /s6 /
COPY --from=idc-build /ucsschool-id-connector/ /ucsschool-id-connector/
COPY examples/ /ucsschool-id-connector/examples/
COPY s6-rc.d/ /etc/s6-overlay/s6-rc.d
VOLUME /var/log
EXPOSE 8911
ENTRYPOINT ["/init"]
CMD ["/command/with-contenv", "queue_management"]

ARG app_id
ARG commit
ARG date
ARG version

LABEL "description"="Image of UCS app 'UCS@school ID Connector' ('$app_id')."
LABEL "url"="https://www.univention.com/products/univention-app-center/app-catalog/$app_id/"
LABEL "version"="$version"
LABEL "release date"="$date"
LABEL "commit"="$commit"
