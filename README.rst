UCS\@school ID Connector developer documentation
================================================

|python| |license| |code style|

Introduction
------------

All documentation regarding installation and configuration that is relevant for administrators, can be found in ``src/README.rst``.

Interactions and components
^^^^^^^^^^^^^^^^^^^^^^^^^^^

|diagram_details|

Development
-----------

Setup development environment::

    $ cd ~/git/ucsschool-id-connector
    $ make setup_devel_env
    $ make install

This will create a directory ``venv`` with a Python virtualenv with the app and all its dependencies in it. To use it, run::

    $ . venv/bin/activate

Run ``make`` without argument to see more useful commands::

    $ make

    clean                remove all build, test, coverage and Python artifacts
    clean-build          remove build artifacts
    clean-pyc            remove Python file artifacts
    clean-test           remove test and coverage artifacts
    setup_devel_env      setup development environment (virtualenv)
    lint                 check style (requires Python interpreter activated from venv)
    format               format source code (requires Python interpreter activated from venv)
    test                 run tests with the Python interpreter from 'venv'
    coverage             check code coverage with the Python interpreter from 'venv'
    coverage-html        generate HTML coverage report
    install              install the package to the active Python's site-packages
    build-docker-img     build docker image locally quickly
    build-docker-img-on-knut copy source to docker.knut, build and push docker image


Build Docker image::

    $ cd ~/git/ucsschool-id-connector
    $ make build-docker-img

The Docker image can be started on its own (but won't receive JSON files in the in queue from the listener in the host) by running::

    $ docker run -p 127.0.0.1:8911:8911/tcp --name ucsschool_id_connector docker-test-upload.software-univention.de/ucsschool-id-connector:1.0.0

Use ``docker run -d ...`` to let it run in the background. Use ``docker logs ucsschool_id_connector`` to see the stdout; ``docker stop ucsschool_id_connector`` and ``docker rm ucsschool_id_connector`` to stop and remove the running container.

Replace version (in above command ``1.0.0``) with current version. See ``APP_VERSION`` in output at the start of the build process.


When the container is started that way (not through the appcenter) it must be accessed through https://FQDN:8911/ucsschool-id-connector/api/v1/docs after stopping the firewall (``service univention-firewall stop``).

To enter the running container run::

    $ docker exec -it ucsschool_id_connector /bin/ash

(When started through the appcenter use ``univention-app shell ucsschool-id-connector``.)

Inside the container you can use the virtual envs Python::

    /ucsschool-id-connector # . venv/bin/activate

    (venv) /ucsschool-id-connector # python
    Python 3.7.4 (default, Aug  2 2019, 18:24:02)
    [GCC 8.3.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from ucsschool_id_connector import models

    (venv) /ucsschool-id-connector # ipython
    Python 3.7.4 (default, Aug  2 2019, 18:24:02)
    Type 'copyright', 'credits' or 'license' for more information
    IPython 7.8.0 -- An enhanced Interactive Python. Type '?' for help.

    In [1]: from ucsschool_id_connector import models


Install BB-API on sender for integration tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A HTTP-API is required for the integration tests (running in the container) to be able to create/modify/delete users in the host and the target systems::

    $ ucr set bb/http_api/users/django_debug=yes bb/http_api/users/wsgi_server_capture_output=yes bb/http_api/users/wsgi_server_loglevel=debug bb/http_api/users/enable_session_authentication=yes
    $ cp /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json /var/lib/ucs-school-import/configs/user_import.json
    $ python -c 'import json; fp = open("/var/lib/ucs-school-import/configs/user_import.json", "r+w"); config = json.load(fp); config["configuration_checks"] = ["defaults", "mapped_udm_properties"]; config["mapped_udm_properties"] = ["phone", "e-mail", "organisation"]; fp.seek(0); json.dump(config, fp, indent=4, sort_keys=True); fp.close()'
    $ echo -e "deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-min-brandenburg/all/\ndeb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-min-brandenburg/amd64/" > /etc/apt/sources.list.d/30_BB.list
    $ univention-install -y ucs-school-http-api-bb

To allow the integration tests to access the APIs it needs a way to retrieve the IP addresses and authentication tokens (To be executed on the sender system)::

    $ /usr/share/pyshared/bb/http_api/users/manage.py shell -c "from rest_framework.authtoken.models import Token; print(Token.objects.first().key)" > /var/www/bb-api-key_sender.txt
    $ ssh IP_TRAEGER1 '/usr/share/pyshared/bb/http_api/users/manage.py shell -c "from rest_framework.authtoken.models import Token; print(Token.objects.first().key)"' > /var/www/bb-api-key_traeger1.txt
    $ ssh IP_TRAEGER2 '/usr/share/pyshared/bb/http_api/users/manage.py shell -c "from rest_framework.authtoken.models import Token; print(Token.objects.first().key)"' > /var/www/bb-api-key_traeger2.txt
    $ echo IP_TRAEGER1 > /var/www/bb-api-IP_traeger1.txt
    $ echo IP_TRAEGER2 > /var/www/bb-api-IP_traeger2.txt

Using devsync with running app container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sync your working copy into the running container, enter it and restart the services::

    [test VM] $ docker inspect --format='{{.GraphDriver.Data.MergedDir}}' "$(ucr get appcenter/apps/ucsschool-id-connector/container)"
    → /var/lib/docker/overlay2/8dc58fa1022e173cdd2a08153c1585043f0253b413ac9982a391a74150a2f387/merged
    [developer machine] ~/git/ucsschool-id-connector $ devsync -v src/ 10.200.3.66:/var/lib/docker/overlay2/8dc58fa1022e173cdd2a08153c1585043f0253b413ac9982a391a74150a2f387/merged/ucsschool-id-connector/
    [test VM] $ univention-app shell ucsschool-id-connector
    [in container] $ /ucsschool-id-connector/venv/bin/pip3 install --no-cache-dir -r src/requirements.txt -r src/requirements-dev.txt
    [in container] $ /etc/init.d/ucsschool-id-connector restart
    [in container] $ /etc/init.d/ucsschool-id-connector-rest-api stop
    [in container] $ /etc/init.d/ucsschool-id-connector-rest-api-dev start
    #                       auto-reload HTTP-API ^^^^

    [in container] $ src/schedule_user demo_teacher
    # DEBUG: Searching LDAP for user with username 'demo_teacher'...
    # INFO : Adding user to in-queue: 'uid=demo_teacher,cn=lehrer,cn=users,ou=DEMOSCHOOL,dc=uni,dc=dtr'.
    # DEBUG: Done.

    [in container] $ . venv/bin/activate
    [in container] (venv) $ cd src
    [in container] (venv) $ python -m pytest -l -v


Build release
-------------

To upload ("push") a new Docker image to Univentions Docker registry (``docker-test.software-univention.de``), run::

    $ cd ~/git/ucsschool-id-connector
    $ make build-docker-img-on-knut


Tests
-----

Unit tests are executed as part of the build process. To start them manually in the installed apps running Docker container, run::

    root@ucs-host:# univention-app shell ucsschool-id-connector
    /ucsschool-id-connector # cd src/
    /ucsschool-id-connector/src # /ucsschool-id-connector/venv/bin/python -m pytest -l -v tests/unittests
    /ucsschool-id-connector/src # exit

To run integration tests (*not safe, will modify source and target systems!*), run::

    root@ucs-host:# univention-app shell ucsschool-id-connector
    /ucsschool-id-connector # cd src/
    /ucsschool-id-connector/src # /ucsschool-id-connector/venv/bin/python -m pytest -l -v tests/integration_tests
    /ucsschool-id-connector/src # exit



.. |license| image:: https://img.shields.io/badge/License-AGPL%20v3-orange.svg
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3.7+-blue.svg
    :alt: Python 3.7+
    :target: https://www.python.org/downloads/release/python-373/
.. |code style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style: black
    :target: https://github.com/python/black
.. |diagram_overview| image:: src/static/ucsschool-id-connector_overview.png
    :alt: Diagram with an overview of the master 2 master sync
.. |diagram_details| image:: src/static/ucsschool-id-connector_details.png
    :alt: Diagram with the technical details of the master 2 master sync
