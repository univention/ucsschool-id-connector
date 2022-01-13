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
    $ pre-commit run -a

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

*All commands in the Makefile assume that the virtualenv is active.*

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

Inside the container you can use the systems Python::

    /ucsschool-id-connector # python3
    Python 3.8.2 (default, Feb 29 2020, 17:03:31)
    [GCC 9.2.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from ucsschool_id_connector import models

    /ucsschool-id-connector # ipython
    Python 3.8.2 (default, Feb 29 2020, 17:03:31)
    Type 'copyright', 'credits' or 'license' for more information
    IPython 7.13.0 -- An enhanced Interactive Python. Type '?' for help.

    In [1]: from ucsschool_id_connector import models


Install Kelvin API on sender for integration tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A HTTP-API is required for the integration tests (running in the container) to be able to create/modify/delete users in the host and the target systems::

    $ univention-app install ucsschool-kelvin-rest-api
    $ cp /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json /var/lib/ucs-school-import/configs/user_import.json
    $ python -c 'import json; fp = open("/var/lib/ucs-school-import/configs/user_import.json", "r+w"); config = json.load(fp); config["configuration_checks"] = ["defaults", "mapped_udm_properties"]; config["mapped_udm_properties"] = ["displayName", "e-mail", "organisation", "phone"]; fp.seek(0); json.dump(config, fp, indent=4, sort_keys=True); fp.close()'

To allow the integration tests to access the APIs it needs a way to retrieve the IP addresses. Username "Administrator" and password "univention" is assumed. To be executed on the sender system::

    $ echo IP_TRAEGER1 > /var/www/IP_traeger1.txt
    $ echo IP_TRAEGER2 > /var/www/IP_traeger2.txt


Integration tests for ID Broker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run the ID Broker tests the following steps are needed::

    $ echo IP_IDBroker > /var/www/IP_idbroker.txt
    $ echo IP_TRAEGER1 > /var/www/IP_traeger1.txt

The ``IP_TRAEGER1`` is necessary to test if of the ID Broker plugin can be used aside to the
Kelvin plugins. If you do not want to test this scenario, add the pytest mark ``not id_broker_compatibility``
when you execute the tests.

The integration tests for the ID Broker plugin are not using SSL. To achieve this you have to set the environment
 variable ``UNSAFE_SSL`` on the target system inside the UCS\@school APIs container::

    $ univention-app shell ucsschool-apis sh -c 'export UNSAFE_SSL=1 && /etc/init.d/ucsschool-apis restart'

Inside the ID Connector container run::

    $ univention-app shell ucsschool-id-connector  sh -c 'export UNSAFE_SSL=1 && /etc/init.d/ucsschool-id-connector restart'

Before running the integration tests, make sure to remove all remaining school_authority configurations.
To run only the tests for the ID Broker plugin, run::

    $ univention-app shell ucsschool-id-connector sh -c "export UNSAFE_SSL=1 && cd src/tests && pytest -lv -m 'id_broker'"


Using devsync with running app container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sync your working copy into the running container, enter it and restart the services::

    [test VM] $ docker exec "$(ucr get appcenter/apps/ucsschool-id-connector/container)" /etc/init.d/ucsschool-id-connector stop
    [test VM] $ docker inspect --format='{{.GraphDriver.Data.MergedDir}}' "$(ucr get appcenter/apps/ucsschool-id-connector/container)"
    → /var/lib/docker/overlay2/8dc58fa1022e173cdd2a08153c1585043f0253b413ac9982a391a74150a2f387/merged
    [developer machine] ~/git/ucsschool-id-connector $ devsync -v src/ 10.200.3.66:/var/lib/docker/overlay2/8dc58fa1022e173cdd2a08153c1585043f0253b413ac9982a391a74150a2f387/merged/ucsschool-id-connector/
    [test VM] $ univention-app shell ucsschool-id-connector
    [in container] $ python3 -m pip install --no-cache-dir -r src/requirements.txt -r src/requirements-dev.txt
    [in container] $ python3 -m pip install -e src/
    [in container] $ /etc/init.d/ucsschool-id-connector restart
    [in container] $ /etc/init.d/ucsschool-id-connector-rest-api stop
    [in container] $ /etc/init.d/ucsschool-id-connector-rest-api-dev start
    #                       auto-reload HTTP-API ^^^^

    [in container] $ src/schedule_user demo_teacher
    # DEBUG: Searching LDAP for user with username 'demo_teacher'...
    # INFO : Adding user to in-queue: 'uid=demo_teacher,cn=lehrer,cn=users,ou=DEMOSCHOOL,dc=uni,dc=dtr'.
    # DEBUG: Done.

    # Log is in /var/log/univention/ucsschool-id-connector/queues.log

    [in container] $ cd src
    [in container] $ python3 -m pytest -l -v


Build release
-------------

* Update the apps version in ``VERSION.txt``.
* Add an entry to ``src/HISTORY.rst``.
* Build and push Docker image to Docker registry

To upload ("push") a new Docker image to Univentions Docker registry (``docker-test.software-univention.de``), run::

    $ cd ~/git/ucsschool-id-connector
    $ make build-docker-img-on-knut


Tests
-----

Unit tests are executed as part of the build process. To start them manually in the installed apps running Docker container, run::

    root@ucs-host:# univention-app shell ucsschool-id-connector
    /ucsschool-id-connector # cd src/
    /ucsschool-id-connector/src # python3 -m pytest -l -v tests/unittests
    /ucsschool-id-connector/src # exit

To run integration tests (*not safe, will modify source and target systems!*), run::

    root@ucs-host:# univention-app shell ucsschool-id-connector
    /ucsschool-id-connector # cd src/
    /ucsschool-id-connector/src # python3 -m pytest -l -v tests/integration_tests
    /ucsschool-id-connector/src # exit



.. |license| image:: https://img.shields.io/badge/License-AGPL%20v3-orange.svg
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3.8-blue.svg
    :alt: Python 3.8
    :target: https://www.python.org/downloads/release/python-382/
.. |code style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style: black
    :target: https://github.com/psf/black
.. |diagram_overview| image:: src/static/ucsschool-id-connector_overview.png
    :alt: Diagram with an overview of the master 2 master sync
.. |diagram_details| image:: src/static/ucsschool-id-connector_details.png
    :alt: Diagram with the technical details of the master 2 master sync
