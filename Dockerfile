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

# Compile python 3.8
RUN apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev libbz2-dev wget ca-certificates xz-utils
RUN wget https://python.org/ftp/python/3.8.19/Python-3.8.19.tar.xz && tar -xf Python-3.8.19.tar.xz && mv Python-3.8.19 /usr/local/share/python3.8
RUN cd /usr/local/share/python3.8 && ./configure --enable-optimizations --enable-shared --with-ensurepip=install && make && make altinstall && ldconfig /usr/local/share/python3.8
RUN ln -s /usr/local/bin/python3.8 /usr/bin/python3

# Install python dependencies
COPY src/requirements*.txt /tmp/
RUN python3.8 -m pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

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
    python3.8 -m pip install --no-cache-dir --compile --editable . && \
    rst2html.py README.rst README.html && \
    rst2html.py HISTORY.rst HISTORY.html && \
    rm -rf /ucsschool-id-connector/src/.eggs/ /ucsschool-id-connector/src/.pytest_cache/ /root/.cache/ /tmp/pip*

LABEL "description"="Image of UCS app 'UCS@school ID Connector' ('$app_id')."
LABEL "url"="https://www.univention.com/products/univention-app-center/app-catalog/$app_id/"
LABEL "version"="$version"
LABEL "release date"="$date"
LABEL "commit"="$commit"
