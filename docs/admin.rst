.. This file is formatted in the spirit of
   https://rhodesmill.org/brandon/2012/one-sentence-per-line/
.. include:: <isonum.txt>
.. include:: univention_rst_macros.txt

**************
Administration
**************

Admin overview
==============

.. figure:: images/ucsschool-id-connector_overview_extended.svg
   :width: 700

   Simplified overview of the |IDC|

The |IDC| replication system is composed of four components:

1. An *LDAP server* containing user data.
2. A process on the data source UCS server,
   receiving user creation/modification/deletion events from
   the LDAP server and relaying them to multiple recipients via HTTP,
   called the  |iIDCS|.
3. A process on the data source UCS server to monitor and configure
   the |UAS| |IDC| service,
   called the  |iIDCH|.
4. Multiple recipients of the directory data relayed by the
   |iIDCS|.
   They run an HTTP-API service, that the
   |iIDCS| pushes updates to.




Admin prerequisites
===================

This administration chapter is useful when you need to administer an |IDC| setup,
or you need to integrate |IDC|.
To follow this text, you should be familiar with the following aspects
of the UCS environment:

.. glossary::

LDAP and LDAP listener
   LDAP is used because it is optimized for reading in a hierarchical structure.
   It shouldn't be accessed directly, instead UDM_ should be used.
   OpenLDAP can have plugins, notifier being one of them that is heavily used in UCS.
   Upon changes in the LDAP directory, the notifier triggers listeners locally
   and on remote systems.

   The listener service connects to all local or remote notifiers in the domain.
   The listener, when notified, calls listener modules,
   which are scripts (in shell and python)

   You need to be able to:

   - understand the basic concepts of LDAP

   |rarr| https://docs.software-univention.de/manual/5.0/en/index.html#introduction-ldap-directory-service

.. _UDM:

|UDM|
   |UDM| (**UDM**) is used for handling user data
   (and other data) that is stored in the LDAP server,
   one of two core storage places (the other one is `UCR`_).
   Examples for data are users, roles or machine info.
   UDM adds a layer of functionality and logic on top of LDAP,
   hence LDAP shouldn't be used directly, but only through UDM.

   You need to be able to:

   - understand the concept of UDM
   - know the basic structure of UDM objects and their attributes
   - add and manage extended attributes

   |rarr| https://docs.software-univention.de/developer-reference/5.0/en/udm/index.html  |br|

.. _UCR:

|UCR|
   The |UCR| (**UCR**) stores configuration variables and settings to run the system,
   and creates and changes actual Linux configuration files
   as configured by these variables upon setting said variables.

   You need to be able to:

   - understand basic UCR concepts
   - set and read UCR variables.

   |rarr| `<https://docs.software-univention.de/manual/5.0/en/computers/ucr.html#administration-of-local-system-configuration-with-univention-configuration-registry>`_


|AppC| settings
   The |AppC| is an ecosystem similar to the app stores known from mobile platforms
   like Apple or Google.
   It provides an infrastructure to build, deploy and run enterprise applications
   on |UCS| (UCS).
   The |AppC| uses well-known technologies like Docker.

   Within the app center, you can configure settings for the individual apps.

   - https://docs.software-univention.de/app-center/5.0/en/configurations.html#app-settings
   - https://docs.software-univention.de/manual/5.0/en/software/app-center.html#appcenter-configure


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
   |rarr|  https://docs.software-univention.de/ucsschool-handbuch-5.0.html (german only) |br|

|UAS| |KLV| REST API
   The |UAS| |KLV| REST API (Kelvin) provides HTTP endpoints
   to create and manage individual |UAS| domain objects
   like school users, school classes and schools (OUs).
   It is written in FastAPI, hence in Python 3.

   You need to be able to install and configure Kelvin.

   |rarr| https://docs.software-univention.de/ucsschool-kelvin-rest-api/overview.html |br|
   |rarr| https://docs.software-univention.de/ucsschool-handbuch-5.0.html#structure:ldap

If you want to also develop for the |IDC|, please also see the next chapter :doc:`development`.

Installation
============

Sending system
--------------

The app is available in the |AppC|. You can install it with:

.. code-block:: bash

    $ univention-app install ucsschool-id-connector

This runs the  join script ``50ucsschool-id-connector.inst``, which creates:

* the file ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret``
  containing the key with which JWT tokens are signed.
* the group ``ucsschool-id-connector-admins``
  (with DN ``cn=ucsschool-id-connector-admins,cn=groups,$ldap_base``)
  who's members are allowed to access the |IDC| HTTP-API.

Use of both is explained later on in `Authentication`_

.. note::
   You can check the existence of the group with:

   .. code-block:: bash

         $ udm groups/group list --filter cn=ucsschool-id-connector-admins


.. note::

   Join scripts are registered in LDAP and then executed on any UCS system
   either before/during/after the join process.

   |rarr| https://help.univention.com/t/a-script-shall-be-executed-on-each-or-a-certain-ucs-systems-before-during-after-the-join-process/13034

If the above didn't get created, run:

.. code-block:: bash

    $ univention-run-join-scripts --run-scripts --force 50ucsschool-id-connector.inst

This forces the (re-)running of the join script.

Receiving system
----------------

In order for the |iIDC| app to be able to create/modify/delete users
on the target systems an HTTP-API is required on the target system.
Currently only the Kelvin API is supported.

.. note::
  This only makes sense if the sender and target systems are in different domains,
  because in the same domain, users and groups already get synced using other UCS mechanisms.

Install the |KLV| API on each target system:

.. code-block:: bash

    $ univention-app install ucsschool-kelvin-rest-api

To allow the |iIDC| app on the sender system to access the Kelvin-API on the receiving system,
it needs an authorized user account.
By default, the Administrator account on the receiving system is the only authorized user.
To add a dedicated |KLV| API user for the |UAS| |IDC|
consult the `Kelvin documentation <https://docs.software-univention.de/ucsschool-kelvin-rest-api/>`_
on how to do that.

Configuration
=============

Now that everything is installed, let's configure the setups. We configure the receiving system first,
because we need auth credentials used on the receiving system later on the sending system.

Configure receiving system - HTTP-API (|KLV|)
---------------------------------------------

You need to install and configure the |KLV| API. This is documented in the
`Kelvin documentation <https://docs.software-univention.de/ucsschool-kelvin-rest-api/>`_.

We assume that you have a current version of |KLV| installed after reading the documentation.

.. _kelvin_credentials:

.. note::
   For the authorization of the |iUASIDC| at the target system
   it needs credentials with special privileges.
   Create a user with the name and password of your choice and add him to the group
   ``ucsschool-kelvin-rest-api-admins``.

   .. code-block:: bash

      $ udm users/user create --position "cn=users,$(ucr get ldap/base)" \
        --set username=USERNAME-OF-YOUR-CHOICE --set lastname=Kelvin --set firstname=UCS \
        --set password="PASSWORD-OF-YOUR-CHOICE"

      $ udm groups/group modify --dn "cn=ucsschool-kelvin-rest-api-admins,cn=groups,$(ucr get ldap/base)" \
        --append users="uid=USERNAME-OF-YOUR-CHOICE,cn=users,$(ucr get ldap/base)"

   Note down the credentials, they are needed for the
   :ref:`school authority configuration on the sending system <auth_config>` further down.

   **WARNING**: the password is now in the command history. You might want to delete this using e.g:

   .. code-block:: bash

      $ history -d -2

After installation and basic configuration you might want to configure mapped UDM properties.

Beyond the `standard object properties in UCS@school <https://docs.software-univention.de/ucsschool-kelvin-rest-api/resource-users.html#users-resource-representation>`_
you can define additional UDM properties that should be available in the |KLV| API on the target system.

For this you would define a configuration in ``/etc/ucsschool/kelvin/mapped_udm_properties.json``, e.g.:

.. code-block::

   {
       "user": ["title", "phone", "e-mail"],
       "school": ["description"]
   }

This would make the listed properties available for the ``user`` and ``school`` resources.

|KLV| needs to be restarted after changes to its configuration::

   $ univention-app restart ucsschool-kelvin-rest-api

.. note::
   When configuring |KLV| in detail, remember that the password hashes for LDAP and Kerberos
   authentication are collectively transmitted in one JSON object to one target attribute.
   This means it's all or nothing: all hashes are synced, even if empty.
   You can't select individual hashes.

.. note::
   Please make sure that you configure all the mapped properties that the sending system sends, e.g.
   ``displayName``. If the sender sends more than the receiver is configured to process,
   you will end up with unexpected errors, e.g. ``404`` in the log.




Configure sending system
------------------------

The school authorities configuration must be done through the  |iIDCH|.
Do not edit configuration files directly.

.. _ucs_school_id_connector_http_api:

UCS\@school ID Connector HTTP API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The HTTP-API of the |iIDC| app offers three resources:

* *queues*: monitoring of queues
* *school_authorities*: configuration of school authorities
* *school_to_authority_mapping*:  configuration of which school we sync to which authority

You can discover the API interactively using one of two web interfaces.
They can be visited with a browser at their respective URLs:

.. _swagger_ui:

* `Swagger UI <https://github.com/swagger-api/swagger-ui>`_: ``https://FQDN/ucsschool-id-connector/api/v1/docs``
* `ReDoc <https://github.com/Rebilly/ReDoc>`_: ``https://FQDN/ucsschool-id-connector/api/v1/redoc``

The Swagger UI page is especially helpful as it allows sending queries directly from the browser.
The equivalent ``curl`` command lines are then displayed.

An `OpenAPI v3 (formerly "Swagger") schema <https://swagger.io/docs/specification/about/>`_
can be downloaded from ``https://FQDN/ucsschool-id-connector/api/v1/openapi.json``


Authentication
~~~~~~~~~~~~~~

Only members of the group ``ucsschool-id-connector-admins`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes.
In production, only the regular admin user accounts should be used.

You can authorize yourself in e.g. the Swagger UI using the ``Authorize`` button.

To use the  |iIDCH| from a script, a `JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_
must be retrieved from ``https://FQDN/ucsschool-id-connector/api/token``.
The token will be valid for a configurable amount of time (default 60 minutes),
after which it must be renewed.
To change the TTL of the token, open the corresponding *app settings* in the |AppC|.

Example ``curl`` command to retrieve a token:

.. code-block:: bash

    $ curl -i -k -X POST --data 'username=Administrator&password=s3cr3t' \
      https://FQDN/ucsschool-id-connector/api/token



School authorities mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _Mappings:

We now need to configure two things:

1. What school authorities do we send data to, and what data can they receive? This is described in this section.
2. What actual schools are handled by which receiving system (school authority)? This is described in the
   following section: :ref:`School to authority mapping`.

We start with the first mapping, the one for school authorities.

In order to send user data to the target system, it must be decided
which properties of which objects to send, and more important,
which properties *not* to send.

.. _phone_numbers_example:

E.g. there might be telephone numbers for students in the system on the sending side,
but those should not be made available to the receiving school system.
Instead of forbidding properties, we "map" properties on the sending side
to properties on the receiving side.

.. _example_kelvin_config:

Here is what the mapping related part of an example configuration looks like:

.. code-block::

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
* The *virtual* ``roles`` property should be synced to an |UAS| system as ``roles``

.. note::
   ``roles`` is *virtual* because there is special handling by the |iIDC| app
   mapping ``ucsschoolRole`` to ``roles``.

.. warning::

   When creating users via Kelvin, some attributes are required and therefore have to be present within the mapping::

      {
        "firstname": "firstname",
        "lastname": "lastname",
        "username": "name",
        "school": "school",
        "schools": "schools",
        "roles": "roles",
        "ucsschoolRecordUID": "record_uid",
        "ucsschoolSourceUID": "source_uid"
      }



Here is a complete example that you can also find in the section  :ref:`school-authority-mapping`.

.. literalinclude:: ../examples/school_authority_kelvin.json

.. _auth_config:

These are the keys in the configuration:

- *name* identifies a specific receiving system. It is a free-form string. Adapt
  to your needs - and remember it, we need it in the next step.
- *username* and *password* are the credentials that are needed on the receiving system. Use the
  :ref:`credentials you created when configuring the receiving system <kelvin_credentials>`.
- The systems address is specified using *url*.
- The users *mapping* inside *plugin_configs["kevlin"]* is as described above, only a bit longer.
- We also have a mapping for *school_classes*, which sets up the sync for those groups.
- *sync_password_hashes* - if password hashed should be synced.
- *ssl_context* - contains values that are passed to the
  `ssl context object <https://docs.python.org/3.8/library/ssl.html#ssl.SSLContext>`_
  which is used to communicate with the receiving system.
- *active* - configures if this configuration for a an out queue for a school authority is active (
  so you don't have to delete it).
- *plugins* - which plugins are going to be used for this school authority. Usually just "kelvin".

Please adapt this to your needs, of course. The complete and adapted configuration needs to be posted
to the ``school_authorities`` resource in the :ref:`Swagger UI <swagger_ui>`.

.. _school_to_authority_mapping:

School to authority mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the second of the two :ref:`mappings <Mappings>` we need.

While the above mapping defines which school authorities we have, we now need to map which school we
sync to which authority - an authority could handle more than one school, so it's an 1:n mapping.

The format is:

.. code-block::

   {
     "mapping": {
       "NAME_OF_SCHOOL": "NAME_OF_RECIPIENT",
       "ANOTHER_SCHOOL": "OTHER_OR_SAME_RECIPIENT",
       ...
      }
   }

You can have one or more schools in the mapping.

So assuming you have a ``DEMOSCHOOL`` on your sending system, and you used the above configuration
to define ``Traeger1`` as a recipient system, you could do:

.. code-block::

   {
     "mapping": {
       "DEMOSCHOOL": "Traeger1"
      }
   }

.. note::

   :ref:`Remember?<l10n>` ``Traeger`` refers to the receiving side of the sync process

You can also find this example in :ref:`school-to-authority-mapping`.



Please "PUT" this configuration JSON to the ``school_to_authority_mapping`` resource
in the :ref:`Swagger UI<swagger_ui>`.





Role specific attribute mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
  This is an advanced scenario. If you don't need this,
  jump to the :ref:`next section <Trying it out>`.

Back to our  :ref:`example about telephone numbers <phone_numbers_example>`.
Imagine that while telephone numbers should not be transferred for students,
they are actually needed for teachers.
This means, that we have a need to define per role which properties should be transferred.

With version ``2.1.0`` role specific attribute mapping was added to the default |KLV| plugin.
This allows to define additional user mappings for each role (``student``, ``teacher``, ``staff``
and ``school_admin``)
by adding a new mapping next to the ``users`` mapping suffixed by ``_$ROLE``,
e.g. ``users_student: {}``.

If a user object is handled by the |KLV| plugin, the mapping is determined as follows:

1. Determine the schools the current school authority is configured to handle.
2. Determine all roles the user has in these schools.
3. Order the roles by priority: ``school_admin`` being the highest, followed by ``staff``, ``teacher``
   and then ``student``.
4. Find a ``users_$ROLE`` mapping from the ones configured in the plugin settings, pick the one
   with the highest priority (from step 3).
5. If none was found, fall back to the ``users`` mapping as the default.

.. _school_classes_problem_0:

An example for such a configuration can be found in :ref:`role-specific-kelvin-plugin-mapping`

.. note::
   The priority order for the roles was chosen in order of common specificity in |UAS|.
   A student only ever has the role ``student``.
   But teachers, staff and school admins can have multiple roles.

.. note::
   The mappings for the different roles are not additive
   because that approach would complicate the option to remove mappings from a specific role.
   Therefore, only *one* mapping is chosen by the rules just described.

.. _school_classes_problem_1:

.. warning::



   Users have the field ``school_classes``, which describes which school classes they belong to.
   You might want to prevent certain user roles from being added or removed to school classes.
   Please be aware that leaving out the ``school_classes`` from the mapping is not sufficient to achieve this:
   changing the school classes of a user does not only result in a user change event
   but also a school class change event, which needs to be handled separately. You therefore need to use
   a derivative of the |KLV| plugin, which is described in the next section.


Partial group sync mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
  This is an advanced scenario. If you don't need this,
  jump to the :ref:`next section <Trying it out>`.

Remember that in the last examples we had a property
that we would send for some users, but not others, depending on their role?
Turns out that we can have the same problem for groups.

Imagine that a school manages locally which teachers belong to which class.
In the role specific mapping we would *not* sync the classes attribute ``school_classes``,
preventing overwriting the local managed settings (:ref:`see above <school_classes_problem_1>`).
This is not enough though: we would also need to make sure that we don't sync
the property ``users`` of groups which contains those teachers.

With version ``2.1.0`` a new derivative of the |KLV| plugin was added:
``kelvin-partial-group-sync``. This plugin alters the handling of school class changes
by allowing you to specify a list of roles that should be ignored when syncing groups.
The following steps determine which members are sent to a school authority
when a school class is added:

1. Add all users that are members of the school class locally (Normal |KLV| plugin behavior).
2. Remove all users that have a configured role to ignore in any school
   handled by the school authority configuration.
3. Get all members of the school class on the target system that have one of the configured roles
   and add them.
4. Get all members of the school class on the target system that are unknown to the |IDC|
   and add them.

This results in school classes having only members with roles not configured to ignore, |br|

+ members with roles to ignore that were added on the target system, |br|
+ any users added on the target system which are unknown to the ID Connector.

.. warning::
   To achieve this behavior, several additional LDAP queries on the |IDC|
   and one additional request to the target system are necessary.
   This affects performance.

To activate this alternative behavior replace the ``kelvin`` plugin in a school authority configuration
with ``kelvin-partial-group-sync``.
The configuration options are exactly the same as for the ``kelvin`` plugin,
except for the addition of ``school_classes_ignore_roles``,
which holds the list of user roles to ignore for school class changes.

See :ref:`partial-groupsync` for an example configuration.

.. warning::
   Please be aware that this plugin can only alter the handling of dedicated school class change events.
   Due to the technical situation, changing the members of a school class often results in two events,
   a school class change and a user change.
   To actually prevent users of certain roles being added to school classes at all,
   it is necessary to leave out the mapping of the users ``school_class`` field
   in the configuration as well - :ref:`see above <school_classes_problem_0>`.

Trying it out
=============

Time has come to try it out. What we want to do:

1. Create a test user
2. Import the test user on the sending side
3. and watch the user being synced to the receiving side.

.. note:

  Only users with the properties  "ucsschoolRecordUID" and "ucsschoolSourceUID"
  are synced. We need to make sure that the user(s) we use for testing have
  these properties.



The slow way would be to  `create a user`_   individually (and make sure to amend the
required properties),
or to use the |UAS| import.
You can read all about importing users in the `Import CLI manual (german only)`_.

We however do it the fast way, creating and importing the user in one step:

.. code-block:: bash

   $ /usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
     --students 1  --classes 1 DEMOSCHOOL

This will create a user within a class in the school ``DEMOSCHOOL``.

Now watch the log file to see the sync action on the *sender system*:

.. code-block:: bash

   $ tail -f /var/log/univention/ucsschool-id-connector/queues.log

In another terminal on the *receiving system* you can see the user being received by the
|KLV| API:

.. code-block:: bash

   $ tail -f /var/log/univention/ucsschool-kelvin-rest-api/http.log # kelvin log

You might need to wait a short moment before the queue picks up the new user. If everything went fine,
you should see some messages in the kelvin log, and you can confirm that the user was created in
either the |KLV| web interface at ``https://FQDN/ucsschool/kelvin/v1/docs`` or in the UMC.

These log files are also a good starting point for debugging in case something went wrong.

.. hint::

   When debugging always make sure that the following is correct and matches:

   1. school authority configuration on the sender system (including auth credentials)
   2. school to  authority mapping on the sender system
   3. ``mapped_udm_properties.json`` on the receiving system has all extra attributes that are
      defined in the school authority mapping.

Good luck! :-)


Starting / Stopping services
============================

Both services (|iIDCS| and  |iIDCH|) run in a Docker container.
The container can be started/stopped by using the regular service facility of the host system:

.. code-block:: bash

    $ univention-app start ucsschool-id-connector
    $ univention-app status ucsschool-id-connector
    $ univention-app stop ucsschool-id-connector
    $ univention-app restart ucsschool-id-connector

To restart individual services, the init scripts *inside* the Docker container can be used.
The ``univention-app`` program has a command that makes it easy to execute commands *inside*
the Docker container:

.. code-block:: bash

    # UCS@School ID Connector service
    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector restart

    # UCS@School ID Connector HTTP API
    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector-rest-api start


Updates
=======
Updates are installed in one of the two usual UCS ways. Either via UMC or on the command line:

.. code-block:: bash

    $ univention-upgrade

    # or just:

    $ univention-app upgrade ucsschool-id-connector

Extra: setting up a second school authority
=============================================

If we already have a school authority set up and want to set up a second one
(by copying its configuration) we can do the following:

1. Make sure the new school authority server has the |KLV| app installed and running.

2. Retrieve the configuration for our old school authority.

   For this we open the HTTP-API Swagger UI ( ``https://FQDN/ucsschool-id-connector/api/v1/docs``)
   and authenticate ourselves. The button can be found in the top right corner of the page.

   Then we retrieve a list of the available school authorities
   by using the ``GET /ucsschool-id-connector/api/v1/school_authorities`` tab,
   by clicking on ``Try it out`` and ``Execute``.

   In the response body, we get a JSON list of the school authorities that are currently configured.
   We need to copy the one we want to replicate and save it for later.

3. Under ``POST /ucsschool-id-connector/api/v1/school_authorities`` we can create the new school authority.

   Click *try it out* and insert the copied JSON object from before into the request body.

   Now we just have to alter the name, URL, and login credentials before executing the request.

   - The URL has to point to the new school authorities HTTP-API.
   - The name can be chosen at your leisure
   - The password is the authentication token of the school authorities HTTP-API (retrieved earlier).

The tab ``PATCH /ucsschool-id-connector/api/v1/school_authorities/{name}`` can be used
to change an already existing configuration.

To retrieve a list of the extended attributes on the old school authority server, one can use:

.. code-block:: bash

    $ udm settings/extended_attribute list


.. _create a user: https://help.univention.com/t/how-a-ucs-school-user-should-look-like/15630#a-sample-command-9

.. _Import CLI manual (german only): https://docs.software-univention.de/ucsschool-import-handbuch-5.0.html

.. spelling::

   Schulbetreiber
