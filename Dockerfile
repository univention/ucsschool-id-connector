ARG UCS_BASE_IMAGE_TAG=0.12.0
ARG UCS_VERSION=520

FROM gitregistry.knut.univention.de/univention/components/ucs-base-image/ucs-base-${UCS_VERSION}:${UCS_BASE_IMAGE_TAG}

ARG app_id
ARG commit
ARG date
ARG version

ARG S6_OVERLAY_VERSION=3.1.6.2

VOLUME /var/log

WORKDIR /ucsschool-id-connector

EXPOSE 8911

RUN apt-get install -y build-essential python3 python3-dev python3-pip xz-utils

# Install python dependencies
COPY src/requirements*.txt /tmp/
RUN python3 -m pip install --break-system-packages --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

# Add S6
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz
COPY s6-rc.d/ /etc/s6-overlay/s6-rc.d
ENTRYPOINT ["/init"]
CMD ["/command/with-contenv", "/ucsschool-id-connector/src/queue_management"]

# install app
COPY src/ /ucsschool-id-connector/src/
COPY VERSION.txt /ucsschool-id-connector
COPY examples/ /ucsschool-id-connector/examples/
RUN cd /ucsschool-id-connector/src && \
    python3 -m pip install --break-system-packages --no-cache-dir --compile --editable . && \
    rst2html README.rst README.html && \
    rst2html HISTORY.rst HISTORY.html && \
    rm -rf /ucsschool-id-connector/src/.eggs/ /ucsschool-id-connector/src/.pytest_cache/ /root/.cache/ /tmp/pip*

LABEL "description"="Image of UCS app 'UCS@school ID Connector' ('$app_id')."
LABEL "url"="https://www.univention.com/products/univention-app-center/app-catalog/$app_id/"
LABEL "version"="$version"
LABEL "release date"="$date"
LABEL "commit"="$commit"
