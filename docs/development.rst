.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. include:: <isonum.txt>
.. include:: univention_rst_macros.txt

.. _dev:
.. _dev-overview:

***********
Development
***********

This section is for software developers who want to setup an environment to develop |UAS| |IDC|.
It provides an overview of the architecture,
the components and their interactions.

.. _fig-containers-simplified:

.. figure:: images/id-connector-containers-simplified.*
   :width: 400

   |IDC| - Containers (`C4 Style <https://c4model.com/>`_)

.. include:: legend.txt

:numref:`fig-containers-simplified` shows the C4 style of :numref:`fig-connector-overview` from the last chapter :doc:`admin`:

* The *school management software* that runs on the state level,
  and exports user data in a file format, for example CSV.

* |iUAS| *import* which is a Python script to import users into a *DC Primary UCS* system.

* The *DC Primary UCS* system passes on the user and group data
  to the actual |iIDC| running in a Docker container.

* The |iIDC| finally writes user and group data to the school authorities.

:numref:`fig-containers` is a simplification. It's on a container level, in the sense used by
the `C4 model <https://c4model.com/>`_.

.. note::

   Arrows in C4 model diagrams are in the direction of data flow.
   It should be apparent from the source and target nodes what the label on the
   arrow refers to.

Development prerequisites
=========================

This section assumes that you are already familiar with the section :ref:`admin`,
and the :ref:`admin-definitions` described therein.

You also need the following knowledge to follow this manual and to develop for |IDC|:

HTTP
   The foundation of data communication for the internet.
   The |IDC| APIs use HTTP.
   You need to understand:

   * HTTP messages
   * authentication concepts
   * error codes

   |rarr| https://developer.mozilla.org/en-US/docs/Web/HTTP

Python and :program:`pytest`
   The Python programming language and its testing module.
   You need to:

   * program and debug Python modules
   * test Python source code, ideally using :program:`pytest`

   |rarr| https://www.python.org |br|
   |rarr| https://pytest.org

:program:`FastAPI`
   |IDC| uses the :program:`FastAPI` framework for the APIs.
   You need to understand:

   * :program:`FastAPI`
   * dependency injection
   * *Pydantic* models

   |rarr| https://fastapi.tiangolo.com/ |br|
   |rarr| https://docs.pydantic.dev/latest/

Docker
   Software to isolate software and run them in containers.
   You need to:

   * understand :file:`Dockerfile` basics
   * run containers
   * understand mounts

   |rarr| https://www.docker.com/

:program:`Pluggy`
   :program:`Pluggy` is the :program:`pytest` plugin system.
   You need to understand basic concepts of hook specifications,
   hook implementation and hook calling.

   |rarr| https://pluggy.readthedocs.io/en/latest/

UDM REST API (optional)
   A HTTP REST API which you can use to inspect, modify, create, and delete
   UDM objects through HTTP requests.

   You only need to know about the UDM REST API
   if you want to access extra information about objects
   within your custom plugin.
   You need to understand:

   * the structure of UDM objects.
   * how to read and maybe write UDM objects, according to your needs.

   |rarr| https://docs.software-univention.de/developer-reference/5.0/en/udm/rest-api.html

:program:`pre-commit` (optional)
   A framework for managing and maintaining multi-language :program:`pre-commit` hooks.
   You only need :program:`pre-commit`, if you commit to the Univention |IDC| repository.
   You need to understand:

   * how to install :program:`pre-commit` definitions.
   * how to run :program:`pre-commit` checks.
   * be aware of using different virtual environments for writing code and running :program:`pre-commit`.

   |rarr| https://pre-commit.com/

Interactions and components
===========================

This section describes the interactions between the components.

Overview, less simplified
-------------------------

:numref:`fig-containers` shows the containers for the |IDC|.

.. _fig-containers:

.. figure:: images/id-connector-containers.*
   :width: 400

   |IDC| containers

.. include:: legend.txt

Compared to :numref:`fig-containers-simplified`, the additional element is *Large in-queue* on the left in the middle.
It's a folder which interacts as the interface between the *Primary Directory Node* and the |iIDC|.
JSON files are written to the folder, and then read out.

The *get extra data* arrow is an interaction from the |IDC| when it might need
extra data that isn't contained in the JSON files.

.. _dev-primary:

Primary Directory Node
----------------------

:numref:`fig-containers-ucs` gives a detailed view on the *UCS DC* component
located between *UCS\@school import* and *Large in-queue*. This section
describes the elements in detail.

.. _fig-containers-ucs:

.. figure:: images/id-connector-container-ucs.*
   :width: 700

   ID Connector Primary Directory Node components

.. include:: legend.txt

The |iUCS| *import* is a Python script, that reads data such as CSV data,
and writes the contained user and group data to the *LDAP*.
As mentioned in the diagram,
there are other mechanisms that modify the LDAP, the UMC being one of them.
The point is that user and group data *somehow* arrives.

The LDAP machinery then calls the |iIDC| *ID Connector listener* Python script is.
The *ID Connector listener* handles the write events that are of interest for the |IDC|.

In a first step, the *ID Connector listener* writes this data to the *small in-queue*,
a folder containing minimal information in JSON format,
namely the type of change, such as add, update, delete,
and the ``entryUUID`` of the concerned object.

The *ID Connector listener* doesn't write the data directly to the *Converter* for the
following reasons:

1. Speed by decoupling - the LDAP listeners should be able to do their job as fast as possible,
   and shouldn't have to wait for the next processing steps.
   Hence, the folder acts as a queue, and only writes minimal data.

2. The folder can also act as an entry point for debugging and manual insertion of user data.
   For example, you want to reschedule a user without import the user again.

   * To write some JSON data into this folder, use the :command:`schedule_user` script.

   * Or for groups, use the :command:`schedule_group` script.

   * To add JSON data into the folder for all school users and school groups,
     use the :command:`schedule_school` script.

The *Converter* runs as a daemon,
picks up the JSON files from the *small in-queue*,
and fetches the actual data from the *LDAP* using the ``python-ldap``.
It then puts a JSON representation of the UDM Object into the *Large in-queue*.

In turn, the |iIDC| running in a Docker container reads the *Large in-queue*.

ID Connector
------------

:numref:`fig-container-docker` shows the *ID Connector* component between
*Large in-queue* and the *School authority*. This section describes the elements
in detail.

.. _fig-container-docker:

.. figure:: images/id-connector-container-docker.*
   :width: 700

   ID Connector components

.. include:: legend.txt

As described in :ref:`dev-primary`, the *Primary Directory Node* writes data to the *Large in-queue*.
The host UCS system and the |iIDC| Docker container can access the *Large in-queue* folder.
The Docker container actually mounts the folder.

*In Queue* is a Python process, that reads the *Large in-queue*.
It may need extra data from the LDAP on the *Primary Directory Node*,
which it fetches using ``python-ldap``.
For caching purposes, it uses an :program:`SQLite` database as a caching mechanism,
called the *UUID record cache*.

The *In Queue* decides, what user and group data to send where.
It uses the :ref:`school-to-authority-mapping` for decision in the process.
For each potential recipient there is a separate *Out queue*.
It writes user and group data in JSON format into the respective folder.

The plugin processes pick up the JSON data, for example *Out A*.
Usually there is only the ``Kelvin ID Connector plugin``, which helps |IDC| to talk to Kelvin REST APIs.
The Kelvin plugin process then talks to Kelvin API on the *School authority A*,
doing the final transmission of the user and group data.

The *Management REST API* orchestrates the processes and manages the outgoing queues.

.. hint::

    To read more about *Management REST API*, see :ref:`ucs-school-id-connector-http-api`.


Complete picture
----------------

The complete picture is a bit crowded. If you want see it anyway, here are your choices:

.. dropdown:: Complete overview, C4 style

    .. figure:: images/id-connector-unified.*
       :width: 800

       The |IDC| overview in C4 style

    .. include:: legend.txt


.. dropdown:: Overview, manually drawn, with file locations

    .. figure:: images/ucsschool-id-connector_details2.*
       :width: 800

       The |IDC|, *not* simplified.


Setup for development
=====================

This section describes the setup of |IDC| for development.

Running the |IDC| requires an LDAP, listeners etc., so you really need a complete UCS installation.
Hence, you rather have a local checkout on the development machine,
and then synchronize the code changes into an |IDC| container that runs on a virtual machine.
:numref:`fig-dev-setup` shows a C4 model for the relationship
between the developer's local system writing changes to the UCS system used for development.

.. _fig-dev-setup:

.. figure:: images/dev_setup.*
   :width: 700

   Setup for development

.. include:: legend.txt

The following sections describe the setup for development for the |IDC|:

* You have a :command:`git checkout` of the ``ucsschool-id-connector`` repository on your *development machine*.

* To synchronize the changes,
  you use the script :program:`devsync` to synchronize changes on your *development machine*.

* You synchronize the changes to the corresponding :file:`installation` folder of the |iIDC| Docker container.

.. hint::

   If you don't have :program:`devsync`, a Univention internal script from the ``toolshed`` repository,
   you might as well use :program:`scp`, :program:`rsync`, or any other transfer mechanism
   of your liking to copy changes to a remote system.

Machine
-------

To set up the local development environment, run the following commands.
They create the directory :file:`venv` with a Python virtual environment with the app and all its dependencies in it.

.. code-block:: console

   # clone ucsschool-id-connector
   $ cd ucsschool-id-connector
   $ make setup_devel_env
   $ . venv/bin/activate
   $ make install
   $ pre-commit run -a

To *activate* the Python virtual environment in the :file:`venv` directory,
run the following command:

.. code-block:: console

   $ . venv/bin/activate


.. warning::

    All commands in the :file:`Makefile` assume
    that you **activated** the Python virtual environment.

To see the commands, run :command:`make` without argument:

.. code-block:: console

   $ make

    clean                 remove all build, test, coverage and Python artifacts
    clean-build           remove build artifacts
    clean-pyc             remove Python file artifacts
    clean-test            remove test and coverage artifacts
    setup_devel_env       setup development environment (virtualenv)
    lint                  check style (requires Python interpreter activated from venv)
    format                format source code (requires Python interpreter activated from venv)
    test                  run tests with the Python interpreter from 'venv'
    coverage              check code coverage with the Python interpreter from 'venv'
    coverage-html         generate HTML coverage report
    install               install the package to the active Python's site-packages


Run unit tests
--------------

Unit tests run as part of the :ref:`build process <dev-build-artifacts>`.
To start the units tests manually inside the |IDC| Docker container,
run the following commands:

.. code-block:: bash

   root@ucs-host:# univention-app shell ucsschool-id-connector
   $ cd src/
   $ python3 -m pytest -l -v tests/unittests
   $ exit


Plugin development
==================

.. py:currentmodule:: ucsschool_id_connector.plugins

This section describes how to develop a plugin for |IDC|.

How does the plugin system work?
--------------------------------

You can enhance the |iUASIDC| through plugins.
|IDC| uses the `pluggy <https://pluggy.readthedocs.io/en/latest/>`_ plugin system
to define, implement, and call plugins.

.. seealso::

   To get a short impression on *Pluggy*, have a look at the
   `toy example <https://pluggy.readthedocs.io/en/latest/#a-toy-example>`_
   in the *Pluggy* documentation.

The basic idea for plugins is the following:

* specify hook specifications: callables with the signature you
  want to have, decorated with a ``hook_spec`` marker provided by
  :py:func:`pluggy.HookspecMarker`.

* write actual hook implementations, also known as *plugins* that |IDC| calls later:
  callables with the same name and signature as in the specification,
  but this time decorated with a ``hook_impl`` marker provided by
  :py:func:`pluggy.HookimplMarker`.

The |IDC| system already defines the :py:data:`hook_spec` and :py:data:`hook_impl` markers.
You can use them directly.
The same is true for finding and calling your custom plugin.

The key file for |IDC| in this context is :file:`src/ucsschool_id_connector/plugins.py`,
where you find the :py:data:`hook_spec` and :py:data:`hook_impl` markers.
In this file you also find the plugin *specifications* as function signatures,
decorated with the ``@hook_spec`` decorator.

The app provides default plugins,
that implement a default version for all specifications found in :file:`src/ucsschool_id_connector/plugins.py`.
Search for ``@hook_impl`` in :file:`src/plugins` to find them.

The |IDC| uses some of the default plugins only if no custom plugins are present.
See usages of
:py:func:`filter_plugins`
defined in :file:`src/ucsschool_id_connector/plugins.py`:

* :py:meth:`~Postprocessing.create_request_kwargs`
* :py:meth:`~Postprocessing.school_authority_ping`
* :py:meth:`~Postprocessing.handle_listener_object`

A simple custom plugin
----------------------

The following demonstrates a simple example of a custom plugin for |IDC|.

You find the directory structure for your custom plugins
and packages on the host system in :file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/`.
For packages, see the :ref:`plugin-development-advanced-example` below:

* :file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/plugins/packages/`

* :file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/plugins/plugins/`

You can put a file containing a plugin class into the :file:`plugins/plugins` directory.
For example, you can save the following content into a file called :file:`myplugin.py`:

.. code-block:: python

   from ucsschool_id_connector.utils import ConsoleAndFileLogging
   from ucsschool_id_connector.plugins import hook_impl, plugin_manager
   logger = ConsoleAndFileLogging.get_logger(__name__)

   class MyPlugin:

       @hook_impl
       def get_listener_object(self, obj_dict):
           logger.info("Myplugin runs get_listener_obj with %r", obj_dict)

   plugin_manager.register(MyPlugin())

Restart the |IDC|:

.. code-block:: bash

   $ univention-app restart ucsschool-id-connector

Validate the queues log file in the directory
:file:`/var/log/univention/ucsschool-id-connector/queues.log`
and find entries like this:

.. code-block::

   2021-12-13 14:32:52 INFO  [ucsschool_id_connector.plugin_loader.load_plugins:79] Loaded plugins:
   [...]
   2021-12-13 14:32:52 INFO  [ucsschool_id_connector.plugin_loader.load_plugins:81]     'myplugin.MyPlugin': ['get_listener_object']

The entries tell you that the |IDC| found your plugin :py:class:`MyPlugin`
and the hook implementation for :py:meth:`~MyPlugin.get_listener_object`.

.. _plugin-development-advanced-example:

Advanced example
----------------

In this example, you learn how to additionally:

* define your own hook specifications.
* use an extra package for shared code across plugins.

The directory structure for a custom plugin ``dummy`` and custom package :py:mod:`example_package`
inside :file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/` looks as the following:

.. code-block:: bash

   .../plugins/
   .../plugins/packages
   .../plugins/packages/example_package
   .../plugins/packages/example_package/__init__.py
   .../plugins/packages/example_package/example_module.py
   .../plugins/plugins
   .../plugins/plugins/dummy.py

.. note::

   Putting the :py:mod:`example_package` into the :file:`packages` directory solves an import problem.
   The module loader in the :file:`plugin_loader.py` file appends the :file:`packages` directory
   to the Python :external+python:py:data:`sys.path`.
   The |IDC| imports packages herein without being *properly* installed.

.. code-block:: python
   :caption: Content of :file:`plugins/packages/example_package/example_module.py`

   #
   # An example Python module that will be loadable as "example_package.example_module"
   # if stored in 'plugins/packages/example_package/example_module.py'.
   # Do not forget to create 'plugins/packages/example_package/__init__.py'.
   #

   from ucsschool_id_connector.utils import ConsoleAndFileLogging

   logger = ConsoleAndFileLogging.get_logger(__name__)


   class ExampleClass:
       def add(self, arg1, arg2):
           logger.info("Running ExampleClass.add() with arg1=%r arg2=%r.", arg1, arg2)
           return arg1 + arg2


.. code-block:: python
   :caption: Content of :file:`plugins/plugins/dummy.py`

   #
   # An example plugin that will be usable as "plugin_manager.hook.dummy_func()".
   # It uses a class from a module in a custom package:
   # plugins/packages/example_package/example_module.py
   #

   from ucsschool_id_connector.utils import ConsoleAndFileLogging
   from ucsschool_id_connector.plugins import hook_impl, hook_spec, plugin_manager
   from example_package.example_module import ExampleClass

   logger = ConsoleAndFileLogging.get_logger(__name__)

   class DummyPluginSpec:
       @hook_spec(firstresult=True)
       def dummy_func(self, arg1, arg2):
           """An example hook."""

   class DummyPlugin:
       @hook_impl
       def dummy_func(self, arg1, arg2):  # <-- this must match the specification!
           """
           Example plugin function.

           Returns the sum of its arguments.
           Uses a class from a custom package.
           """
           logger.info("Running DummyPlugin.dummy_func() with arg1=%r arg2=%r.", arg1, arg2)
           example_obj = ExampleClass()
           res = example_obj.add(arg1, arg2)
           assert res == arg1 + arg2
           return res


   # register plugins
   plugin_manager.register(DummyPlugin())


Upon app startup, the |IDC| discovers all plugins and logs them in the log file.
You find successful messages like this in the queues log file in the
:file:`/var/log/univention/ucsschool-id-connector/queues.log`
directory:

.. code-block:: bash

   ...
   INFO  [ucsschool_id_connector.plugins.load_plugins:83] Loaded plugins: {.., <dummy.DummyPlugin object at 0x7fa5284a9240>}
   INFO  [ucsschool_id_connector.plugins.load_plugins:84] Installed hooks: [.., 'dummy_func']
   ...

.. _dev-build-artifacts:

Build artifacts
===============

This section describes how to build the |IDC| artifacts, such as the Docker
image and the release image.

Build Docker image
------------------

The repository contains a :file:`Dockerfile` that you can use to build a Docker image.

.. warning::

   Don't use the image for production.
   It's suitable for testing and development purposes.

.. _dev-build-docker-image-manual-start:

.. code-block:: bash
   :caption: Manually start the |IDC| Docker container

   $ docker run -p 127.0.0.1:8911:8911/tcp --name ucsschool_id_connector \
     docker-test-upload.software-univention.de/ucsschool-id-connector:$(python3 -c "import tomllib; print(tomllib.load(open('src/pyproject.toml', 'rb'))['tool']['poetry']['version'])")

.. note::

   When you start the |IDC| Docker container manually as shown in :numref:`dev-build-docker-image-manual-start`,
   and not through the |AppC|,
   you need to stop the local firewall with
   :command:`service univention-firewall stop`
   and can then access the container through the URL
   ``https://FQDN:8911/ucsschool-id-connector/api/v1/docs``.


You can also:

.. code-block:: bash

   # let it run in the background.
   $ docker run -d ...

   # see the stdout
   $ docker logs ucsschool_id_connector

   # stop the running container
   $ docker stop ucsschool_id_connector

   # remove the container
   $ docker rm ucsschool_id_connector

To enter the running container run:

.. code-block:: bash

   $ docker exec -it ucsschool_id_connector /bin/ash



Build release image
-------------------

.. warning::

   You need to be a software developer at Univention to use this section.

To build a release image, use the following steps:

#. Update the app version in :file:`src/pyproject.toml`.

#. Add an entry to the changelog in :file:`src/HISTORY.rst`.

#. Adjust the
   `app ini file <https://git.knut.univention.de/univention/components/ucsschool-id-connector/-/blob/master/appcenter_scripts/ucsschool-id-connector.ini?ref_type=heads>`_,
   if needed.

#. The repository pipeline builds the Docker image automatically.

#. Use the dedicated Jenkins job.
   The job tags the image
   and also updates the Docker image in the App Provider Portal.

#. Verify that the Jenkins job correctly set the tag
   for the Docker image of the app
   in the App Provider Portal.

Integration tests
=================

Univention has automated integration tests using Jenkins.
The Jenkins configuration file locates at
https://github.com/univention/univention-corporate-server/blob/5.0-6/test/scenarios/autotest-244-ucsschool-id-sync.cfg.
If you want to manually set up integration tests,
you need to look there for hints on how to do it.
