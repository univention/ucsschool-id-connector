FROM alpine:3.12

ARG app_id
ARG commit
ARG date
ARG version

VOLUME /var/log

WORKDIR /ucsschool-id-connector

EXPOSE 8911

CMD ["/sbin/init"]

LABEL "description"="Image of UCS app 'UCS@school ID Connector' ('$app_id')." \
    "url"="https://www.univention.com/products/univention-app-center/app-catalog/$app_id/" \
    "version"="$version" \
    "release date"="$date" \
    "commit"="$commit"

# package and Python dependency installation, base system configuration,
# and uninstallation - all in one step to keep image small
COPY alpine_apk_list.* init.d/ src/requirements*.txt /tmp/
RUN echo '@stable-community http://dl-cdn.alpinelinux.org/alpine/latest-stable/community' >> /etc/apk/repositories && \
    apk add --no-cache --virtual mybuilddeps $(cat /tmp/alpine_apk_list.build) && \
    apk add --no-cache $(cat /tmp/alpine_apk_list.runtime) && \
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
   # install Python packages
    python3 -m pip install --no-cache-dir --compile --upgrade pip wheel && \
    # build ujson from source https://github.com/esnme/ultrajson/issues/326
    python3 -m pip install --no-cache-dir --compile git+https://github.com/esnme/ultrajson.git@2.0.3 && \
    python3 -m pip install --no-cache-dir --compile -r /tmp/requirements.txt -r /tmp/requirements-dev.txt && \
    rm -rf /root/.cache/ /tmp/* && \
    apk del --no-cache mybuilddeps

# install app
COPY src/ /ucsschool-id-connector/src/
COPY VERSION.txt /ucsschool-id-connector
COPY examples/ /ucsschool-id-connector/examples/
RUN cd /ucsschool-id-connector/src && \
    python3 -m pip install --no-cache-dir --compile --editable . && \
    rst2html5-3 README.rst README.html && \
    rst2html5-3 HISTORY.rst HISTORY.html && \
    rm -rf /ucsschool-id-connector/src/.eggs/ /ucsschool-id-connector/src/.pytest_cache/ /root/.cache/ /tmp/pip*
