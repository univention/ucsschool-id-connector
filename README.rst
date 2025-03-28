UCS\@school ID Connector developer documentation
================================================

|python| |license| |code style| |renovate|

Introduction
------------

All documentation regarding installation and configuration that is relevant for administrators, can be found in ``src/README.rst``.

Interactions and components
^^^^^^^^^^^^^^^^^^^^^^^^^^^

|diagram_details|

Development
-----------

Setup development environment::

    $ cd ~/git/ucsschool-id-connector/src
    $ poetry install --with dev --with tests


You can ran the unittest::

    $ cd ~/git/ucsschool-id-connector/src
    $ poetry run pytest tests/unittests


Run ``make`` without argument to see more useful commands::

    $ make

    clean                remove all build, test, coverage and Python artifacts
    clean-build          remove build artifacts
    clean-pyc            remove Python file artifacts
    clean-test           remove test and coverage artifacts
    lint                 check style (requires Python interpreter activated from venv)
    format               format source code (requires Python interpreter activated from venv)
    test                 run tests with the Python interpreter from 'venv'
    coverage             check code coverage with the Python interpreter from 'venv'
    coverage-html        generate HTML coverage report


*All commands in the Makefile assume that the virtualenv is active.*


The docker image is built every time something connected to it is pushed. This way you can exchange the docker image on a vm, assuming the ID Connector is installed.

```
$ image="gitregistry.knut.univention.de/univention/components/ucsschool-id-connector:branch-mybranchname"
$ app_name="ucsschool-id-connector"
$ univention-app install $app_name
$ docker pull "$image"
$ univention-app dev-set $app_name "DockerImage=$image"
$ univention-app reinitialize $app_name
```


The Docker image can be started on its own (but won't receive JSON files in the in queue from the listener in the host) by running::

    $ docker run -p 127.0.0.1:8911:8911/tcp --name ucsschool_id_connector docker-test-upload.software-univention.de/ucsschool-id-connector:1.0.0

Use ``docker run -d ...`` to let it run in the background. Use ``docker logs ucsschool_id_connector`` to see the stdout; ``docker stop ucsschool_id_connector`` and ``docker rm ucsschool_id_connector`` to stop and remove the running container.

Replace version (in above command ``1.0.0``) with current version. See version in the pyproject.toml.


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
    $ python -c 'import json; fp = open("/etc/ucsschool/kelvin/mapped_udm_properties.json", "w"); config = {"user": ["pwdChangeNextLogin", "displayName", "e-mail", "organisation", "phone", "title"]}; json.dump(config, fp, indent=4, sort_keys=True); fp.close()'

To allow the integration tests to access the APIs it needs a way to retrieve the hostnames. Username "Administrator" and password "univention" is assumed. To be executed on the sender system::

    $ echo HOSTNAME_TRAEGER1 > /var/www/traeger1.txt
    $ echo HOSTNAME_TRAEGER2 > /var/www/traeger2.txt


Build release
-------------

* Update the apps version in ``src/pyproject.toml``.
* Add an entry to ``src/HISTORY.rst``.

Docker images are build in merge requests and when pushing to main.

* Create a new tag with the version number you want to release, e.g.: 1.1.0
* Wait for the tag pipeline until it reaches the ``do_release`` job
* Is everything looking good so far? The next will make the new version public!
* Start the ``do_release`` job

Close the bugs which are released::


    Updates for UCS@school ID Connector 2.2.5 have been released.

    https://docs.software-univention.de/ucsschool-id-connector/HISTORY.html

    If this error occurs again, please clone this bug.


Automatic documentation build
-----------------------------

Once documentation changes are pushed to the repository, GitLab builds the HTML
deliverable.

The pipeline always builds the HTML and provides the results for review in the
browser. The jobs create environments and provide a link to view the
environment. The jobs in the pipeline are:

* For a feature branch: click on *View app* for ``review/docs/$BRANCH_REF_SLUG/`` on your merge request
* For the default branch: click on *Open* for the staging/docs `environment <https://git.knut.univention.de/univention/components/ucsschool-id-connector/-/environments>`_

To publish the reviewed documentation to docs.univention.de you need to manually
trigger the *production* job in the pipeline. This will commit and push the
documentation to the `docs.univention.de repository
<https://git.knut.univention.de/univention/docs.univention.de>`_ It has it's own
pipeline and there you also need to manually trigger the *production*. See
https://hutten.knut.univention.de/mediawiki/index.php/Docbook#The_publication_of_the_doc_takes_place_via_GitLab
for the last step.


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


Renovate
--------

See the `Dependency Dashboard <https://git.knut.univention.de/univention/components/ucsschool-id-connector/-/issues/67>`_ for open dependency updates.
Choose which updates you want to tackle by checking the corresponding checkbox
and run the `renovate pipeline <https://git.knut.univention.de/univention/components/ucsschool-id-connector/pipelines/new?var[RUN_RENOVATE]=yes>`_ to create merge requests.


.. |license| image:: https://img.shields.io/badge/License-AGPL%20v3-orange.svg
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3-blue.svg
    :alt: Python 3
    :target: https://www.python.org/
.. |code style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style: black
    :target: https://github.com/psf/black
.. |renovate| image:: https://img.shields.io/badge/renovate-enabled-brightgreen.svg
   :alt: Renovate enabled
   :target: https://git.knut.univention.de/univention/components/ucsschool-id-connector/-/issues/67
.. |diagram_overview| image:: src/static/ucsschool-id-connector_overview.png
    :alt: Diagram with an overview of the master 2 master sync
.. |diagram_details| image:: src/static/ucsschool-id-connector_details.png
    :alt: Diagram with the technical details of the master 2 master sync
