.. This file is formatted in the spirit of
   https://rhodesmill.org/brandon/2012/one-sentence-per-line/
.. include:: <isonum.txt>
.. include:: univention_rst_macros.txt


TODO:
 - id-connector -> ID-Connector
 - LDAP and Openldap


**************
Administration
**************

Overview
========

.. figure:: static/ucsschool-id-connector_overview_extended.svg

   Simplified overview of the id-connector

The |IDC| replication system is composed of four components:

1. An *LDAP server* containing user data.
2. A process on the data source UCS server,
   receiving user creation/modification/deletion events from
   the LDAP server and relaying them to multiple recipients via HTTP.
   Henceforth called the  |iIDCS|.
3. A process on the data source UCS server to monitor and configure
   the |UAS| ID Connector service,
   henceforth called the  |iIDCH|.
4. Multiple recipients of the directory data relayed by the
   |iIDCS|.
   They run a HTTP-API service, that the
   |iIDCS| pushes updates to.




Prerequisites
=============
This chapter is useful when you need to administer an id-connector setup,
or you need to integrate id-connector.
To follow this manual you should be familiar with the following aspects
of the UCS environment:

LDAP and LDAP listener
   LDAP is used because it is optimized for reading in a hierarchical structure.
   It shouldn't be accessed directly, instead UDM_ should be used.
   OpenLDAP can have plugins, notifier being one of them that is heavily used in UCS.
   Upon changes in the LDAP directory the notifier triggers listeners locally
   and on remote systems.

   The listener service connects to all local or remote notifiers in the domain.
   The listener, when notified, calls listener modules,
   which are scripts (in shell and python)

   You need to be able to:

   - understand the basic concepts of LDAP

   |rarr| https://docs.software-univention.de/manual-5.0.html#introduction:LDAP_directory_service

.. _UDM:

UDM
   |UDM| (UDM) is used for handling user data
   (and other data) that is stored in the LDAP server,
   one of two core storage places (the other one is `UCR`_).
   Examples for data are users, roles or machine info.
   UDM adds a layer of functionality and logic on top of LDAP,
   hence LDAP shouldn't be used directly, but only through UDM.

   You need to be able to:

   - understand the concept of UDM
   - know the basic structure of UDM objects and their attributes
   - add and manage extended attributes

   |rarr| TODO Nico simple UDM documentation. Where are the basic concepts defined? |br|
   |rarr| https://docs.software-univention.de/developer-reference-5.0.html#chap:udm

.. _UCR:

UCR
   The |UCR| (UCR) stores configuration variables and settings to run the system,
   and creates and changes actual linux configuration files
   as configured by these variables upon setting said variables.

   You need to be able to:

   - understand basic UCR concepts
   - set and read UCR variables.

   |rarr| `<https://docs.software-univention.de/manual-5.0.html#computers:Administration_of_local_system_configuration_with_Univention_Configuration_Registry>`_


Appcenter settings
   The |AppC| is an ecosystem similar to the app stores known from mobile platforms
   like Apple or Google.
   It provides an infrastructure to build, deploy and run enterprise applications
   on |UCS| (UCS).
   The |AppC| uses well-known technologies like Docker.

   Within the app center you can configure settings for the individual apps.

   |rarr| TODO Nico - documentation on how to set app settings. What we have so far is only:

   - https://docs.software-univention.de/app-provider.html#app-settings
   - https://docs.software-univention.de/manual-5.0.html#appcenter-configure



|UAS| basics
   Schools have special requirements for managing what is going on inside them
   (teachers, students, staff, computer rooms, exams, etc.),
   and for managing the relation between multiple schools,
   their operator organizations ("Schulbetreiber"), and possibly
   ministerial departments above them.

   There are several components used within |UAS|,
   |KLV| (see below) being one of them.

   You need to be able to:

   - know about |UAS| objects
   - know the difference between |UAS|-objects and UDM objects

   |rarr| https://help.univention.com/t/how-a-ucs-school-user-should-look-like/15630 |br|
   |rarr|  https://help.univention.com/t/ucs-school-work-groups-and-school-classes/16925 |br|
   |rarr|  https://docs.software-univention.de/ucsschool-handbuch-4.4.html |br|
   |rarr|  TODO Nico english needed, basic concepts would be needed

|UAS| |KLV| REST API
   The |UAS| |KLV| REST API (Kelvin) provides HTTP endpoints
   to create and manage individual |UAS| domain objects
   like school users, school classes, schools (OUs) and computer rooms.
   It is written in fastapi, hence in python3.

   You need to be able to install and configure kelvin.

   |rarr| https://docs.software-univention.de/ucsschool-kelvin-rest-api/overview.html |br|
   |rarr| TODO Nico concepts of properties and mappings (not sample files, but answering the why, and
   describing the problem that |KLV| solves)

   - best so far: https://docs.software-univention.de/ucsschool-handbuch-4.4.html#structure:ldap

If you want to also develop for the id-connector, please also see the next chapter :doc:`development`.

Installation
============

Sending system
--------------

The app is  available in the appcenter. You can install it with::

    $ univention-app install ucsschool-id-connector

This should run the  join script ``50ucsschool-id-connector.inst``, which creates:

* the file ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret``
  containing the key with which JWT tokens are signed.
* the group ``ucsschool-id-connector-admins``
  (with DN ``cn=ucsschool-id-connector-admins,cn=groups,$ldap_base``)
  who's members are allowed to access the ID-Connector HTTP-API.

Use of both is explained later on in `Authentication`_

.. note::
   You can check the existence of the group with::

      udm groups/group list --filter cn=ucsschool-id-connector-admins


.. note::

   Join scripts are registered in LDAP and then executed on any UCS system
   either before/during/after the join process.

   |rarr| https://help.univention.com/t/a-script-shall-be-executed-on-each-or-a-certain-ucs-systems-before-during-after-the-join-process/13034

If the above didn't get created, run::

    $ univention-run-join-scripts --run-scripts --force 50ucsschool-id-connector.inst

This forces the (re-)running of the join script.

Receiving system
----------------

In order for the |iIDC| app to be able to create/modify/delete users
on the target systems an HTTP-API is required on the target system.
Currently only the Kelvin API is supported.

.. note::
  This of course only makes sense if the target system is in a different domain,
  because otherwise users and groups are synced with other UCS mechanisms.

Install the |KLV| api on each target system::

    $ univention-app install ucsschool-kelvin-rest-api

To allow the |iIDC| app on the sender system to access the Kelvin-API on the receiving system,
it needs an authorized user account.
By default the Administrator account on the receiving system is the only authorized user.
To add a dedicated |KLV| API user for the |UAS| ID-Connector
consult the `Kelvin documentation <https://docs.software-univention.de/ucsschool-kelvin-rest-api/>`_
on how to do that.

TODO Nico: link to proper section in documentation
   - write the proper section first

Configuration
=============


Configure sending side
----------------------

The school authorities configuration must be done through the  |iIDCH|.
Do not edit configuration files directly.

UCS\@school ID Connector HTTP API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The HTTP-API of the |iIDC| app offers two resources:

* *queues*: monitoring of queues
* *school_authorities*: configuration of school authorities

You can discover the API interactively using one of two web interfaces.
They can be visited with a browser at their respective URLS:

* `Swagger UI <https://github.com/swagger-api/swagger-ui>`_: https://FQDN/ucsschool-id-connector/api/v1/docs
* `ReDoc <https://github.com/Rebilly/ReDoc>`_: https://FQDN/ucsschool-id-connector/api/v1/redoc

The Swagger UI page is especially helpful as it allows to send queries directly from the browser.
The equivalent equivalent ``curl`` command lines are then displayed.

An `OpenAPI v3 (formerly "Swagger") schema <https://swagger.io/docs/specification/about/>`_
can be downloaded from https://FQDN/ucsschool-id-connector/api/v1/openapi.json


Authentication
~~~~~~~~~~~~~~

Only members of the group ``ucsschool-id-connector-admins`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes.
In production only the regular admin user accounts should be used.

You can authorize yourself in e.g. the Swagger UI using the ``Authorize`` button.

To use the  |iIDCH| from a script, a `JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_
must be retrieved from``https://FQDN/ucsschool-id-connector/api/token``.
The token will be valid for a configurable amount of time (default 60 minutes),
after which it must be renewed.
To change the TTL of the token, open the corresponding *app settings* in the UCS app center.

Example ``curl`` command to retrieve a token::

    $ curl -i -k -X POST --data 'username=Administrator&password=s3cr3t' https://FQDN/ucsschool-id-connector/api/token

School authorities mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to send user data to the target system, it must be decided
which properties of which objects to send, and more important,
which properties *not* to send.
E.g. there might be telephone numbers for students in the system on the sending side,
but those should not be made available on the receiving school system.
Instead of forbidding properties we "map" properties on the sending side
to properties on the receiving side.

.. _example_kelvin_config:

Here is what the mapping related part of an example config looks like::

   ...
    {
        "plugin_configs": {
            "kelvin": {
                "mapping": {
                    "users": {
                        "ucsschoolRecordUID": "record_uid",
                        "ucsschoolSourceUID": "source_uid",
                        "roles": "roles"
                    }
                }
            }
        }
    }
   ...

This configures a mapping for the |KLV| plugin that sends the three defined properties to the
receiving school:

* The UDM ``ucsschoolRecordUID`` property should be synced to an |UAS| system as ``record_uid``.
* The UDM ``ucsschoolSourceUID`` property should be synced to an |UAS| system as ``source_uid``.
* The *virtual* UDM ``roles`` property should be synced to an |UAS| system as ``roles``

.. note::
   ``roles`` is *virtual* because there is special handling by the |iIDC| app
   mapping ``ucsschoolRole`` to ``roles``  TODO Ask Daniel


Here is a complete example that you can also find in   :ref:`simple-kelvin-mapping`.

.. literalinclude:: ../../examples/school_authority_kelvin.json


Please adapt the example to your needs, especially

- url
- username
- password

The complete and adapted example needs to be posted to the ``school_authorities`` resource in the Swagger UI.

School to authority mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO::

   {
     "mapping": {
       "NAME_OF_SCHOOL": "NAME_OF_RECIPIENT",
       ...
      }
   }

COPY and paste example::

   {
     "mapping": {
       "DEMOSCHOOL": "Traeger1",
       ...
      }
   }

:ref:`Remember?<l10n>` ``Traeger`` refers to the receiving side of the sync process

You can also find the example in :ref:`school-to-authority-mapping`.






Role specific attribute mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
  This is an advanced scenario. If you don't need this,
  jump to the section: :ref:`Configure target system - HTTP-API (|KLV|)`.

Back to our example about telephone numbers. Imagine that while telephone numbers should not be
transferred for students, they are actually needed for teachers.
This means, that we have a need to define per role which properties should be transferred.

With version ``2.1.0`` role specific attribute mapping was added to the default |KLV| plugin.
This allows to define additional user mappings for each role (student, teacher, staff, school_admin)
by adding a new mapping next to the ``users`` mapping suffixed by ``_$ROLE``,
e.g. ``users_student: {}``.

If a user object is handled by the |KLV| plugin the mapping is determined as follows:

1. Determine the schools the current school authority is configured to handle.
2. Determine all roles the user has in these schools.
3. Order the roles by priority: ``school_admin`` being the highest followed by ``staff``, ``teacher``
   and then ``student``.
4. Find a ``users_$ROLE`` mapping from the ones configured in the plugin settings, pick the one
   with the highest priority (from step 3).
5. If none was found, fall back to the ``users`` mapping as the default.

.. _school_classes_problem_0:

An example for such a configuration can be found in :ref:`complex-kelvin-mapping`

.. note::
   The priority order for the roles was chosen in order of common specificity in |UAS|.
   A student is usually ever only a student.
   But teachers, staff and school admins can have multiple roles.

.. note::
   The mappings for the different roles are not additive
   because that approach would complicate the option to remove mappings from a specific role.
   Therefore only *one* mapping is chosen by the rules just described.

.. _school_classes_problem_1:

.. note::



   Users have the field ``school_classes``, which describes which school classes they belong to.
   You might want to prevent certain user roles from being added or removed to school classes.
   Please be aware that leaving out the ``school_classes`` from the mapping is not sufficient to achieve this:
   changing the school classes of a user does not only result in a user change event
   but also a school class change event, which needs to be handled separately. You therefore need to use a
   a derivative of the |KLV| plugin, which is described in the next section.


Partial group sync mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
  This is an advanced scenario. If you don't need this,
  jump to the :ref:`next section<Configure target system - HTTP-API (|KLV|)>`.

Remember that in the last examples we had a property
that we would send for some users, but not others, depending on their role?
Turns out that we can have the same problem for groups.

Imagine that a school manages locally which teachers belong to which class.
In the role specific mapping we would *not* sync the classes attribute ``school_classes``,
preventing overwriting the local managed settings (:ref:`see above <school_classes_problem_1>`).
This is not enough though: we would also need to make sure that we don't sync
the property ``users`` of groups which contains those teachers.

With version ``2.1.0`` a new derivative of the ``Kelvin`` plugin was added:
``kelvin-partial-group-sync``. This plugin alters the handling of school class changes
by allowing you to specify a list of roles that should be ignored when syncing groups.
The following steps determine which members are sent to a school authority
when a school class is added:

1. Add all users that are members of the school class locally (Normal |KLV| plugin behavior).
2. Remove all users that have a configured role to ignore in any school
   handled by the school authority configuration.
3. Get all members of the school class on the target system that have one of the configured roles
   and add them.
4. Get all members of the school class on the target system that are unknown to the ID-Connector
   and add them.

This results in school classes having only members with roles not configured to ignore, |br|
plus members with roles to ignore that were added on the target system, |br|
plus any users added on the target system which are unknown to the ID Connector.

.. warning::
   To achieve this behavior several additional LDAP queries on the ID Connector
   and one additional request to the target system are necessary.
   This affects performance.

To activate this alternative behavior replace the ``kelvin`` plugin in a school authority configuration
with ``kelvin-partial-group-sync``.
The configuration options are exactly the same as for the ``kelvin`` plugin,
except for the addition of ``school_classes_ignore_roles``,
which holds the list of user roles to ignore for school class changes.

See :ref:`partial-groupsync` for an example config.

.. note::
   Please be aware that this plugin can only alter the handling of dedicated school class change events.
   Due to the technical situation, changing the members of a school class often results in two events,
   a school class change and a user change.
   To actually prevent users of certain roles being added to school classes at all,
   it is necessary to leave out the mapping of the users ``school_class`` field
   in the configuration as well - :ref:`see above <school_classes_problem_0>`.



Configure target system - HTTP-API (|KLV|)
-------------------------------------------

You need to install and configure the |KLV| api. This is documented in the
`Kelvin documentation <https://docs.software-univention.de/ucsschool-kelvin-rest-api/>`_.

We assume that you have a current version of |KLV| installed after this.

After installation and basic configuration you might want to configure mapped UDM properties.

Beyond the `standard object properties in UCS@school <https://docs.software-univention.de/ucsschool-kelvin-rest-api/resource-users.html?highlight=password#resource-representation>`_
you can define additional UDM properties that should be available in the |KLV| API on the target system.

For this you would define a configuration in ``/etc/ucsschool/kelvin/mapped_udm_properties.json``::

   {
       "user": ["title", "phone", "e-mail"],
       "school": ["description"]
   }

This would make the listed properties available for the ``user`` and ``school`` resources.

.. note::
   When configuring |KLV| in detail, remember that the password hashes for LDAP and Kerberos
   authentication are collectively transmitted in one JSON object to one target attribute.
   This means it's all or nothing: all hashes are synced, even if empty.
   You can't select individual hashes. TODO Ole: better place for this?

Starting / Stopping services
============================

Both services ( |iIDCS| and  |iIDCH|) run in a Docker container.
The container can be started/stopped by using the regular service facility of the host system::

    $ univention-app start ucsschool-id-connector
    $ univention-app status ucsschool-id-connector
    $ univention-app stop ucsschool-id-connector

To restart individual services, init scripts *inside* the Docker container can be used.
The ``univention-app`` program has a command that makes it easy to execute commands *inside*
the Docker container::

    # UCS@School ID Connector service
    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector restart

    # UCS@School ID Connector HTTP API
    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector-rest-api start


Updates
=======
Updates are installed in one of the two usual UCS ways. Either via UMC or on the command line::

    $ univention-upgrade

    # or just:

    $ univention-app upgrade ucsschool-id-connector

Extra: setting up a second school authority
=============================================

If we already have a school authority set up and want to set up a second one
(by copying its configuration) we can do the following:

1. Make sure the new school authority server has the |KLV| app installed and running.

2. Retrieve the configuration for our old school authority.

   For this we open the HTTP-API Swagger UI ( https://FQDN/ucsschool-id-connector/api/v1/doc )
   and authenticate ourselves. The button can be found in the top right corner of the page.

   Then we retrieve a list of the available school authorities
   by using the ``GET /ucsschool-id-connector/api/v1/school_authorities`` tab,
   by clicking on ``Try it out`` and ``Execute``.

   In the response body, we get a JSON list of the school authorities that are currently configured.
   We need to copy the one we want to replicate and save it for later.

3. Under ``POST /ucsschool-id-connector/api/v1/school_authorities`` we can create the new school authority.

   Click *try it out* and insert the copied JSON object from before into the request body.

   Now we just have to alter the name, url, and login credentials before executing the request.

   - The URL has to point to the new school authorities HTTP-API.
   - The name can be chosen at your leisure
   - The password is the authentication token of the school authorities HTTP-API (retrieved earlier).

The tab ``PATCH /ucsschool-id-connector/api/v1/school_authorities/{name}`` can be used
to change an already existing configuration.

To retrieve a list of the extended attributes on the old school authority server one can use::

    $ udm settings/extended_attribute list
