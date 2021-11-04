**************
Administration
**************

Overview
========

.. figure:: static/ucsschool-id-connector_overview_extended.svg

   Simplified overview of the id-connector

The *UCS\@school ID Connector* replication system is composed of four components:

1. An *LDAP server* containing user data.
2. A process on the data source UCS server, receiving user creation/modification/deletion events from
   the LDAP server and relaying them to multiple recipients via HTTP. Henceforth called the
   *UCS\@school ID Connector service*.
3. A process on the data source UCS server to monitor and configure the UCS\@school ID Connector service,
   henceforth called the *UCS\@school ID Connector HTTP API*.
4. Multiple recipients of the directory data relayed by the *UCS\@school ID Connector service*.
   They run a HTTP-API service, that the *UCS\@school ID Connector service* pushes updates to.


The changelog is in the :doc:`HISTORY` file. (TODO: correctly linked?)


Prerequisites
============
This chapter is useful when you need to administer an id-connector setup, or you need to integrate. To actually follow
this manual you should be familiar with the following aspects of the UCS environment:

Ldap and ldap listener
   The openldap LDAP server that contains the user data. LDAP ACLs are used to restrict access. It shouldn't
   be accessed directly, instead the udm library should be used. Openldap can have plugins, notifier being one
   of them that is heavily used in ucs. Upon changes in the ldap directory the notifier triggers listeners
   locally and on remote systems.

   The listener service connects to all local or remote notifiers in the domain. The listener, when notified,
   calls listener modules, which are scripts (in shell and python)

   You need to be able to: TODO

   read more: TODO

UDM
   Univention Directory Management is used for handling user data that is stored in the ldap
   server, one of two core storage places (the other one is ucr). Examples for data are
   users, roles or machine info. Ldap is used (instead of e.g. sql databases) because it is
   optimized for reading in a hierarchical structure. UDM adds a layer of functionality and logic on
   top of ldap, hence ldap shouldn't be used directly.

   You need to be able to: TODO

   read more: TODO


ucr
   The Univention Config Registry. This stores variables and settings to run the system. It also
   creates and changes actual linux configuration files according to these variables.

   You need to be able to: TODO

   read more: TODO

appcenter settings
    Description

   You need to be able to: TODO

   read more: TODO


ucs\@school basics
   Schools have special requirements for managing what is going on inside them (teachers, students,
   staff, computer rooms, exams, etc.), but also managing the relation between multiple schools, their
   operator organizations ("Schulbetreiber"), and possibly ministerial departments above them.

   There are several components within ucs\@school, kelvin (see below) being one of them.

   You need to be able to:
   - know about ucs\@school objects
   - know the difference between ucs\@school-objects and udm objects

   read more: TODO

Kelvin administration
   The UCS\@school Kelvin REST API provides HTTP endpoints to create and manage individual UCS\@school
   domain objects like school users, school classes, schools (OUs) and computer rooms. This is written
   in fastapi, hence in python3.

   You need to be able to install and configure kelvin. TODO

   read more: https://docs.software-univention.de/ucsschool-kelvin-rest-api/overview.html

If you want more, and develop for id-connector, please also see the next chapter :doc:`plugins`.

Installation
============

On the server system
--------------------
The app is  available in the appcenter. You can it install like this::

    $ univention-app install ucsschool-id-connector

This should run the  join script ``50ucsschool-id-connector.inst``, which creates:

* the file ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret`` containing the key with which JWT tokens are signed.
* the group ``ucsschool-id-connector-admins`` (with DN ``cn=ucsschool-id-connector-admins,cn=groups,$ldap_base``) who's members are allowed to access the HTTP-API.

If the files didn't get created, run::

    $ univention-run-join-scripts --run-scripts --force 50ucsschool-id-connector.inst

This forces the (re-)running of the join script.

TODO:
  - what do I do with the keys? `Authentication`_
  - do I need to add users to the group? `Authentication`_


On the target systems
---------------------

TODO:   - do the systems have to be in the same domain?

An HTTP-API is required for the *UCS\@school ID Connector* app to be able to create/modify/delete users on the target systems. Currently only the Kelvin API is supported.

On each target system run::

    $ univention-app install ucsschool-kelvin-rest-api

To allow the *UCS\@school ID Connector* app to access the APIs it needs an authorized user account. By default the Administrator account is the only authorized user. To add a dedicated Kelvin API user for the UCS\@school ID-Connector consult the Kelvin documentation on how to do that. TODO: link to proper section in documentation

Configuration
=============

The school authorities configuration must be done through the *UCS\@school ID Connector HTTP API*. Do not edit configuration files directly.

TODO: where do I find the http api? `UCS\@school ID Connector HTTP API`_

TODO: introduce the mapping

* The UDM ``ucsschoolRecordUID`` property (a.k.a. UCS\@school ``record_uid`` property) should be synced to a UCS\@school system as ``record_uid``.
* The UDM ``ucsschoolSourceUID`` property (a.k.a. UCS\@school ``source_uid`` property) should be synced to a UCS\@school system as ``source_uid``.
* The *virtual* (special handling by the *UCS\@school ID Connector* app) ``roles`` property should be synced as ``roles``::

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

See ``examples/school_authority_kelvin.json`` for an example.

Further information on the configuration of some select plugins can be found further down.

TODO: what are plugins in this context?


UCS\@school ID Connector HTTP API
---------------------------------

A HTTP-API of the *UCS\@school ID Connector* app offers two resources:

* *queues*: monitoring of queues
* *school_authorities*: configuration of school authorities

Two websites exist, that allow to interactively discover the API. They can be visited with a browser at the URLS:

* `Swagger UI <https://github.com/swagger-api/swagger-ui>`_: https://FQDN/ucsschool-id-connector/api/v1/docs
* `ReDoc <https://github.com/Rebilly/ReDoc>`_: https://FQDN/ucsschool-id-connector/api/v1/redoc

The Swagger UI page is especially helpful as it allows to send queries directly from the browser and displays equivalent ``curl`` command lines.

An `OpenAPI v3 (formerly "Swagger") schema <https://swagger.io/docs/specification/about/>`_ can be downloaded from https://FQDN/ucsschool-id-connector/api/v1/openapi.json


Authentication
--------------

To use the API, a `JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_ must be retrieved from ``https://FQDN/ucsschool-id-connector/api/token``. The token will be valid for a configurable amount of time (default 60 minutes), after which they must be renewed. To change the TTL, open the apps *app settings* in the UCS app center.

Example ``curl`` command to retrieve a token::

    $ curl -i -k -X POST --data 'username=Administrator&password=s3cr3t' https://FQDN/ucsschool-id-connector/api/token

Only members of the group ``ucsschool-id-connector-admins`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes. In production only the regular admin user accounts should be used.

Target HTTP-API (Kelvin)
------------------------
The Kelvin API must be version ``1.2.0`` or higher to work with the UCS\@school ID Connector.
The password hashes for LDAP and Kerberos authentication are collectively transmitted in one JSON object to one target attribute.

The ``mapped_udm_properties`` setting lists the names of UDM properties that should be available in the API.
The example configuration above can be created with the following command::

   $ cp /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json \
      /var/lib/ucs-school-import/configs/kelvin.json
   $ python -c 'import json; fp = open("/var/lib/ucs-school-import/configs/kelvin.json", "r+w"); \
      config = json.load(fp); config["configuration_checks"] = ["defaults", "mapped_udm_properties"]; \
      config["mapped_udm_properties"] = ["phone", "e-mail", "organisation"]; fp.seek(0); \
      json.dump(config, fp, indent=4, sort_keys=True); fp.close()'



Kelvin Plugin Konfiguration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Until a full documentation is developed, only some specifics of the default Kelvin plugin are mentioned here

Role specific attribute mapping
...............................

With version ``2.1.0`` role specific attribute mapping was added to the default kelvin plugin. This allows to define
additional user mappings for each role (student, teacher, staff, school_admin) by adding a new mapping next to the
``users`` mapping suffixed by ``_$ROLE``, e.g. ``users_student: {}``.

TODO: example

If a user object is handled by the kelvin plugin the mapping is determined as follows:

1. Determine all roles the user has in the schools the current school authority is configured to handle
2. From that order the roles for priority with the school_admin being the highest followed by staff, teacher and
   then student.
3. Choose a ``users_$ROLE`` mapping in that order from the ones configured in the plugin settings.
4. If none was found, fall back to the ``users`` mapping as the default.

The mappings for the different roles are not additive because an additive approach would complicate the option
to remove mappings from a specific role. Only one mapping is chosen by the rules just described.

The priority order for the roles was chosen in order of common specificity in UCS\@school. A student is usually ever only
a student. But teachers, staff and school admins can have multiple roles of those three.

Please be aware that removing the ``school_classes`` field in particular is not sufficient to prevent certain user roles
from being added or removed from school classes. This is due to the technical situation that changing the school classes
of a user does not only result in a user change event but also a school class change event, which is handled separately
and would add or remove the user in that way. To avoid this problem a derivative of the kelvin plugin can be used, which
is described in the following chapter.

Partial group sync
..................

With version ``2.1.0`` a new derivate of the ``kelvin`` plugin was added: ``kelvin-partial-group-sync``.
This plugin alters the handling of school class changes by allowing you to specify a list of roles that should be
ignored when syncing groups. The following steps determine which members are sent to a school authority when a
school class is added:

1. Add all users that are members of the school class locally (Normal Kelvin plugin behavior).
2. From that remove all users that have a configured role to ignore in any school handled by the school authority configuration.
3. Get all members of the school class on the target system that have one of the configured roles and add them.
4. Get all members of the school class on the target system that are unknown to the ID-Connector and add them.

This results in school classes having only members with roles not configured to ignore, plus members with roles to ignore
that were added on the target system, plus any users added on the target system which are unknown to the ID Connector.

To achieve this behavior several additional LDAP queries on the ID Connector and one additional request to
the target system are necessary.

To activate this alternative behavior replace the ``kelvin`` plugin in a school authority configuration with
``kelvin-partial-group-sync``. The configuration options are exactly the same as for the ``kelvin`` plugin, except for
the addition of ``school_classes_ignore_roles``, which holds the list of user roles to ignore for school class changes.

Please be aware that this plugin can only alter the handling of dedicated school class change events. Due to the
technical situation, changing the members of a school class often results in two events. A school class change and a
user change. To actually prevent users of certain roles being added to school classes at all, it is necessary to remove
the mapping of the users ``school_class`` field in the configuration as well.



Starting / Stopping services
============================

Both services (*UCS\@school ID Connector service* and *UCS\@school ID Connector HTTP API*) run in a Docker container. The container can be started/stopped by using the regular service facility of the host system::

    $ service docker-app-ucsschool-id-connector start
    $ service docker-app-ucsschool-id-connector status
    $ service docker-app-ucsschool-id-connector stop

To restart individual services, init scripts *inside* the Docker container can be used. The ``univention-app`` program has a command that makes it easy to execute commands *inside* the Docker container::

    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector restart  # UCS\@school ID Connector service
    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector-rest-api start # UCS\@school ID Connector HTTP API


Updates
=======
Updates are installed in one of the two usual UCS ways. Either via UMC or on the command line::

    $ univention-upgrade
    $ univention-app upgrade ucsschool-id-connector



Example of setting up a second school authority
===============================================

If we already have a school authority set up and want to basically copy its configuration in order to set up a second one we can do the following:

First make sure the new school authority server has the Kelvin app installed and running. Configuration is described in a later section.

Then we want to retrieve the configuration for our old school authority.
For this we open the HTTP-API Swagger UI ( https://FQDN/ucsschool-id-connector/api/v1/doc ) and authenticate ourselves.
The button can be found at the top right corner of the page.
Then we retrieve a list of the school authorities available using the ``GET /ucsschool-id-connector/api/v1/school_authorities`` tab, by clicking on ``Try it out`` and ``Execute``.
In the response body we get a JSON list of the school authorities that are currently configured.
We need to copy the one we want to replicate and save it for later.
Under "POST /ucsschool-id-connector/api/v1/school_authorities" we can create the new school authority.
Click *try it out* and insert the coped JSON object from before into the request body.
Now we just have to alter the name, url, and login credentials before executing the request.
The url has to point to the new school authorities HTTP-API.
The name can be chosen at your leisure and the password is the authentication token of the school authorities HTTP-API (retrieved earlier).
The tab ``PATCH /ucsschool-id-connector/api/v1/school_authorities/{name}`` can be used to change an already existing configuration.

To retrieve a list of the extended attributes on the old school authority server one can use::

    $ udm settings/extended_attribute list


