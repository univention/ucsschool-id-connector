FROM alpine:latest

ARG version

VOLUME /var/log

WORKDIR /ucsschool-id-connector

EXPOSE 8911

CMD ["/sbin/init"]

LABEL "description"="UCS@school ID Connector" \
    "version"="$version"

COPY alpine_apk_list init.d/ src/requirements*.txt /tmp/

RUN echo '@stable-community http://dl-cdn.alpinelinux.org/alpine/latest-stable/community' >> /etc/apk/repositories && \
    apk add --no-cache $(cat /tmp/alpine_apk_list) && \
    mv -v /tmp/ucsschool-id-connector.initd /etc/init.d/ucsschool-id-connector && \
    mv -v /tmp/ucsschool-id-connector-rest-api.initd.final /etc/init.d/ucsschool-id-connector-rest-api && \
    mv -v /tmp/ucsschool-id-connector-rest-api.initd.dev /etc/init.d/ucsschool-id-connector-rest-api-dev && \
    rc-update add ucsschool-id-connector default && \
    rc-update add ucsschool-id-connector-rest-api default && \
    cp -v /usr/share/zoneinfo/Europe/Berlin /etc/localtime && \
    echo "Europe/Berlin" > /etc/timezone && \
    # Disable getty's
    sed -i 's/^\(tty\d\:\:\)/#\1/g' /etc/inittab && \
    sed -i \
        # Change subsystem type to "docker"
        -e 's/#rc_sys=".*"/rc_sys="docker"/g' \
        # Allow all variables through
        -e 's/#rc_env_allow=".*"/rc_env_allow="\*"/g' \
        # Start crashed services
        -e 's/#rc_crashed_stop=.*/rc_crashed_stop=NO/g' \
        -e 's/#rc_crashed_start=.*/rc_crashed_start=YES/g' \
        # Define extra dependencies for services
        -e 's/#rc_provide=".*"/rc_provide="loopback net"/g' \
        /etc/rc.conf && \
    # Remove unnecessary services
    rm -fv /etc/init.d/hwdrivers \
        /etc/init.d/hwclock \
        /etc/init.d/modules \
        /etc/init.d/modules-load \
        /etc/init.d/modloop && \
    # Can't do cgroups
    sed -i 's/\tcgroup_add_service/\t#cgroup_add_service/g' /lib/rc/sh/openrc-run.sh && \
    sed -i 's/VSERVER/DOCKER/Ig' /lib/rc/sh/init.sh && \
    virtualenv --system-site-packages /ucsschool-id-connector/venv && \
    /ucsschool-id-connector/venv/bin/pip3 install --upgrade pip && \
    # build ujson from source https://github.com/esnme/ultrajson/issues/326
    /ucsschool-id-connector/venv/bin/pip3 install git+git://github.com/esnme/ultrajson.git && \
    /ucsschool-id-connector/venv/bin/pip3 install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt && \
    rm -rf /root/.cache/ /tmp/* && \
    apk del --no-cache \
        g++ \
        gcc \
        git \
        make \
        musl-dev \
        python3-dev

LABEL "description"="UCS@school ID Connector" \
    "version"="$version"

COPY src/ /ucsschool-id-connector/src/

COPY examples/ /ucsschool-id-connector/examples/
RUN cd /ucsschool-id-connector/src && \
    /ucsschool-id-connector/venv/bin/python3 -m pytest -l -v --color=yes tests/unittests && \
    /ucsschool-id-connector/venv/bin/pip3 install --no-cache-dir --editable . && \
    rst2html5-3 README.rst README.html && \
    rst2html5-3 HISTORY.rst HISTORY.html && \
    rm -rf /ucsschool-id-connector/src/.eggs/ /ucsschool-id-connector/src/.pytest_cache/ /root/.cache/ /tmp/pip*
