FROM alpine:edge

ARG version

VOLUME /var/log

WORKDIR /id-sync

EXPOSE 8911

CMD ["/sbin/init"]

COPY apline_apk_list init.d/ src/requirements*.txt /tmp/

RUN echo '@testing http://dl-cdn.alpinelinux.org/alpine/edge/testing' >> /etc/apk/repositories && \
    apk add --no-cache $(cat /tmp/apline_apk_list) && \
    mv -v /tmp/id-sync.initd /etc/init.d/id-sync && \
    mv -v /tmp/id-sync-rest-api.initd.final /etc/init.d/id-sync-rest-api && \
    mv -v /tmp/id-sync-rest-api.initd.dev /etc/init.d/id-sync-rest-api-dev && \
    rc-update add id-sync default && \
    rc-update add id-sync-rest-api default && \
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
        /etc/rc.conf \
    # Remove unnecessary services
    && rm -fv /etc/init.d/hwdrivers \
        /etc/init.d/hwclock \
        /etc/init.d/modules \
        /etc/init.d/modules-load \
        /etc/init.d/modloop && \
    # Can't do cgroups
    sed -i 's/\tcgroup_add_service/\t#cgroup_add_service/g' /lib/rc/sh/openrc-run.sh && \
    sed -i 's/VSERVER/DOCKER/Ig' /lib/rc/sh/init.sh && \
    virtualenv --system-site-packages /id-sync/venv && \
    /id-sync/venv/bin/pip3 install --upgrade pip && \
    /id-sync/venv/bin/pip3 install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt && \
    rm -rf /root/.cache/ /tmp/* && \
    apk del --no-cache \
        gcc \
        make \
        musl-dev \
        python3-dev

LABEL "description"="ID Sync" \
    "version"="$version"

COPY src/ /id-sync/src/

RUN cd /id-sync/src && \
    /id-sync/venv/bin/python3 -m pytest -l -v --color=yes tests/unittests && \
    /id-sync/venv/bin/pip3 install --no-cache-dir --editable . && \
    rst2html5-3 README.rst README.html && \
    rst2html5-3 HISTORY.rst HISTORY.html && \
    rm -rf /id-sync/src/.eggs/ /id-sync/src/.pytest_cache/ /root/.cache/ /tmp/pip*
