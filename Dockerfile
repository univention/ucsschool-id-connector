ARG UCS_BASE_IMAGE_TAG=0.12.0
ARG UCS_VERSION=520

FROM gitregistry.knut.univention.de/univention/components/ucs-base-image/ucs-base-${UCS_VERSION}:${UCS_BASE_IMAGE_TAG} AS idc-base

ARG S6_OVERLAY_VERSION=3.1.6.2
ENV PYTHONUNBUFFERED=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PIPX_BIN_DIR="/usr/local/bin"
ENV VIRTUAL_ENV="/venv"

RUN apt-get install -y python3 python3-venv

ENV POETRY_VERSION=1.7.1

RUN python3 -m venv $VIRTUAL_ENV
# Use the venv enabled python
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /ucsschool-id-connector

# Build steps
FROM idc-base as idc-build

RUN apt-get install -y build-essential python3-dev xz-utils pipx
RUN pipx install poetry=="$POETRY_VERSION"

# Add S6
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN mkdir /s6
RUN tar -C /s6 -Jxpf /tmp/s6-overlay-noarch.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C /s6 -Jxpf /tmp/s6-overlay-x86_64.tar.xz

COPY src/ /ucsschool-id-connector/src/

RUN cd /ucsschool-id-connector/src/ && poetry install --compile --with dev,test
RUN cd /ucsschool-id-connector/src && \
    poetry run rst2html.py README.rst README.html && \
    poetry run rst2html.py HISTORY.rst HISTORY.html
RUN cd /ucsschool-id-connector/src/ && poetry install --compile --sync --only main
RUN cd /ucsschool-id-connector/src/ && poetry export --format requirements.txt --with test --output=/ucsschool-id-connector/requirements-test.txt

# install app
FROM idc-base as idc-prod

COPY --from=idc-build $VIRTUAL_ENV $VIRTUAL_ENV
COPY --from=idc-build /s6 /
COPY --from=idc-build /ucsschool-id-connector/ /ucsschool-id-connector/
COPY VERSION.txt /ucsschool-id-connector
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
