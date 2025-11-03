.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. This file is formatted in the spirit of
   https://sembr.org/

.. include:: <isonum.txt>
.. include:: univention_rst_macros.txt

.. _admin:

**************
Administration
**************

This section describes the administration tasks for the |IDC|.
It covers the topics installation,
configuration of the sending system and the receiving systems
and lifecycle tasks for the connector.

The |IDC| replication system consists of the following components
as shown in :numref:`fig-connector-overview`:

1. An *LDAP server* containing user data.

2. A process on the data source UCS server,
   receiving user creation/modification/deletion events from
   the LDAP server and relaying them to multiple recipients through HTTP,
   called the  |iIDCS|.

3. A process on the data source UCS server to monitor and configure
   the |UAS| |IDC| service,
   called the |iIDCH|.

4. Multiple recipients of the directory data relayed by the |iIDCS|.
   They run an HTTP-API service, that the |iIDCS| pushes updates to.

.. _fig-connector-overview:

.. figure:: images/ucsschool-id-connector_overview_extended.*
   :width: 700

   Simplified overview of the |IDC|

.. _admin-definitions:

Definitions
===========

For the administration of and |IDC| setup or the integration with |IDC|,
you need to make sure to know about the following aspects of a UCS environment.

.. glossary::

   LDAP and LDAP listener
      UCS uses LDAP because of its optimization for reading in a hierarchical structure.
      Don't accessed directly, use :term:`UDM` instead.
      OpenLDAP can have plugins, such as the notifier UCS heavily uses.
      Upon changes in the LDAP directory, the notifier triggers listeners locally
      and on remote systems.

      The listener service connects to all local or remote notifiers in the domain.
      When notified, the listener calls listener modules, which are scripts in shell and Python.

      You need to understand the basic concepts of LDAP.

      .. seealso::

         For more information, see :ref:`introduction-ldap-directory-service` in :cite:t:`uv-manual`.

   |UDM|
      UCS uses |UDM| (**UDM**) for handling user data and other data stored in the LDAP server.
      The LDAP server is one of two core storage locations.
      The other storage location is :term:`UCR`.
      Examples for data are users, roles, or machine info.

      UDM adds a layer of functionality and logic on top of LDAP,
      hence don't use LDAP directly, but only through UDM.

      You need to:

      * understand the concept of UDM.
      * know the basic structure of UDM objects and their attributes.
      * add and manage extended attributes.

      .. seealso::

         For more information in a developer context, see :ref:`chap-udm` in
         :cite:t:`uv-developer-reference`.

         For an architecture overview, see :external+uv-architecture:ref:`services-udm`
         in :cite:t:`uv-architecture`.

   |UCR|
      |UCR| (**UCR**) stores configuration variables and settings to run the system,
      creates and changes actual configuration text files
      as configured by these variables upon setting said variables.

      You need to:

      * understand basic UCR concepts.
      * know how to set and read UCR variables.

      .. seealso::

         For more information, see
         :ref:`computers-administration-of-local-system-configuration-with-univention-configuration-registry`
         in :cite:t:`uv-manual`.

         For an architecture overview, see :external+uv-architecture:ref:`services-ucr`
         in :cite:t:`uv-architecture`.

   |AppC| settings
      |AppC| is an ecosystem similar to app stores known from mobile platforms
      such as Apple or Google.
      It provides an infrastructure to deploy and run enterprise applications
      on |UCS| (UCS).
      The |AppC| uses well-known technologies like Docker.

      Within the App Center, you can configure settings for the individual apps.

      .. seealso::

         For more information, see the following resources:

         * :ref:`app-settings` in :cite:t:`uv-appcenter`
         * :ref:`appcenter-configure` in :cite:t:`uv-manual`


   |UAS| basics
      Schools have special requirements for managing entities about what is going on inside them,
      such as teachers, students, staff, computer rooms, exams, and more.
      For managing the relation between multiple schools,
      their operator organizations ("Schulbetreiber"), and possibly
      ministerial departments above them.

      .. FIXME : The sentence above is unclear to me.

      There are several components used within |UAS|,
      and |KLV| is one of them.

      You need to:

      * know about |UAS| objects.
      * know the difference between |UAS| objects and UDM objects.

      .. seealso::

         For more information, see the following resources:

         * :uv:kb:`How a UCS\@school user should look like <15630>`
         * :uv:kb:`UCS\@school work groups and school classes <16925>`
         * :external+uv-ucsschool-manual:doc:`index`

   |UAS| |KLV| REST API
      The |UAS| |KLV| REST API (Kelvin) provides HTTP endpoints
      to create and manage individual |UAS| domain objects
      such as school users, school classes and schools (OUs).
      It uses :program:`FastAPI`, hence in :program:`Python 3`.

      You need to be able to install and configure Kelvin.

      .. seealso::

         For more information, see the following resources:

         * :external+uv-ucsschool-kelvin-rest-api:doc:`overview` in
           :cite:t:`uv-ucsschool-kelvin-rest-api`

         * :ref:`structure-ldap` in
           :cite:t:`uv-ucsschool-manual`

If you want to also develop for the |IDC|, please also see the following section :ref:`dev`.

.. _admin-install:

Installation
============

This section describes the installation of the |UAS| |IDC| app.
For a working setup,
you need a sending system with the |IDC| app,
and receiving systems with the |UAS| |KLV| REST API.

Sending system
--------------

The |UAS| |IDC| app is available in the |AppC|.
You can install it with the following command:

.. code-block:: bash

    $ univention-app install ucsschool-id-connector

The installation process runs the join script ``50ucsschool-id-connector.inst``
and creates the following:

* a key for signing the JWT tokens in the file
  :file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret`.

* the group ``ucsschool-id-connector-admins``
  with the distinguished name (DN) ``cn=ucsschool-id-connector-admins,cn=groups,$ldap_base``,
  whose members can access the |IDC| HTTP-API.

The section :ref:`auth` explains both files in detail.

If the installation process didn't create the files listed before,
you can re-run the join script with the following command.

.. code-block:: bash

    $ univention-run-join-scripts --run-scripts --force 50ucsschool-id-connector.inst

.. tip::

   You can validate the existence of the group with:

   .. code-block:: bash

      $ udm groups/group list --filter cn=ucsschool-id-connector-admins

.. tip::

   The installation process registers join scripts in the LDAP
   and runs them on any UCS system before, during, or after the join process.

   For more information,
   see :uv:kb:`A script shall be executed on each or a certain UCS systems before/during/after the join process <13034>`

The app is using the CA trust store from the UCS host system. The app is restarting if the certificates are updated by ``update-ca-certificates``, you can disable the automatic restart in the |AppC| settings.

Receiving system
----------------

The |UAS| |IDC| app needs an HTTP-API on the target system
to create, modify, and delete users.
The |IDC| supports |UAS| |KLV| REST API.

The |UAS| |IDC| app synchronizes users for different domains
between a sender and receiving systems.
UCS takes care of the user synchronization within the domain.

To install the |KLV| API on each receiving system, run the following command:

.. code-block:: bash

    $ univention-app install ucsschool-kelvin-rest-api

To allow the |UAS| |IDC| app on the sender system to access the Kelvin-API on the receiving system,
it needs an authorized user account.
By default, the ``Administrator`` account on the receiving system is the only authorized user.
To add a dedicated |KLV| API user for the |UAS| |IDC|,
consult :cite:t:`uv-ucsschool-kelvin-rest-api`.

If the receiving system is using a private CA, you need to add that CA to the UCS system you installed the |UAS| |IDC| app on.

.. _configure-receiver:

Configure receiving system - HTTP-API (|KLV|)
=============================================

You need to install and configure the |KLV| API as described in
:cite:t:`uv-ucsschool-kelvin-rest-api`.
The following sections assume that you have installed the current version of |KLV|.

.. _kelvin_credentials:

.. note::
   For the authorization of the |iUASIDC| at the target system
   it needs credentials with special privileges.
   Create a user account with the name and password of your choice
   and add them to the group ``ucsschool-kelvin-rest-api-admins``.

   .. code-block:: bash

      $ udm users/user create --position "cn=users,$(ucr get ldap/base)" \
        --set username=USERNAME-OF-YOUR-CHOICE --set lastname=Kelvin --set firstname=UCS \
        --set password="PASSWORD-OF-YOUR-CHOICE"

      $ udm groups/group modify --dn "cn=ucsschool-kelvin-rest-api-admins,cn=groups,$(ucr get ldap/base)" \
        --append users="uid=USERNAME-OF-YOUR-CHOICE,cn=users,$(ucr get ldap/base)"

   Write down the credentials.
   You need them for the
   :ref:`school authority configuration on the sending system <auth-config>`.

   .. warning::

      You used the password before as input to a command.
      It's now in the command history.
      It's recommended to delete the command with the password from the command history.
      Run the following command:

      .. code-block:: bash

         $ history -d -2

After installation and basic configuration you can configure mapped UDM properties.

Beyond the :ref:`standard object properties in UCS\@school <users-resource-repr>`,
you can define additional UDM properties
and make them available in the |KLV| API on the target system.

#. To define additional UDM properties, you first create a mapping in the
   configuration file :file:`/etc/ucsschool/kelvin/mapped_udm_properties.json`.
   The following example makes the listed properties additionally available for
   the resources ``user`` and ``school``.

   .. code-block:: json

      {
          "user": ["title", "phone", "e-mail"],
          "school": ["description"]
      }

#. Restart |KLV| with the following command,
   for the configuration changes to take effect:

   .. code-block:: console

      $ univention-app restart ucsschool-kelvin-rest-api

.. caution::

   When configuring |KLV| in detail, the password hashes for LDAP and Kerberos
   authentication are collectively transmitted in one JSON object to one target attribute.
   This means it's all or nothing: all hashes are synced, even if empty.
   You can't select individual hashes.

.. caution::

   Ensure that you configure all the mapped properties that the sending system sends,
   for example ``displayName``.
   If the sender sends more than the receiver is configured to process,
   you experience unexpected errors, for example ``404`` in the log file.

.. _configure-sender:

Configure sending system
========================

The school authorities configuration must be done through the  |iIDCH|.
Don't edit configuration files directly.

.. _ucs-school-id-connector-http-api:

UCS\@school ID Connector HTTP API
---------------------------------

The HTTP-API of the |iIDC| app offers the following resources:

:samp:`https://{FQDN}/ucsschool-id-connector/api/v1/queues/`
   ``/queues/`` for the monitoring of queues

:samp:`https://{FQDN}/ucsschool-id-connector/api/v1/school_authorities/`
   ``/school_authorities/`` for the configuration of school authorities

:samp:`https://{FQDN}/ucsschool-id-connector/api/v1/school_to_authority_mapping/`
   ``/school_to_authority_mapping/`` for the configuration of which school you want to synchronize to which authority

You can discover the API interactively using one of two web interfaces.
You can visit them with a browser at their respective URLs:

.. _swagger-ui:

* `Swagger UI <https://github.com/swagger-api/swagger-ui>`_: :samp:`https://{FQDN}/ucsschool-id-connector/api/v1/docs`
* `ReDoc <https://github.com/Redocly/redoc>`_: :samp:`https://{FQDN}/ucsschool-id-connector/api/v1/redoc`

The Swagger UI page is especially helpful as it allows sending queries directly from the browser.
The equivalent ``curl`` command lines are then displayed.
You can download an `OpenAPI v3 (formerly "Swagger") schema <https://swagger.io/docs/specification/about/>`_
from :samp:`https://{FQDN}/ucsschool-id-connector/api/v1/openapi.json`.

.. _auth:

Authentication
--------------

Only users being member of the group ``ucsschool-id-connector-admins`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes.
In production, you should only use the regular administration user accounts.

You can authorize yourself, for example in the Swagger UI using the :guilabel:`Authorize` button.

To use the |iIDCH| from a script,
the script must retrieve a
`JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_
from :samp:`https://FQDN/ucsschool-id-connector/api/token`.
The token is valid for a configurable amount of time,
the default value for the time to life (TTL) is 60 minutes.
To change the TTL of the token,
open the corresponding *app settings* in the |AppC|.

.. code-block:: bash
   :caption: Example :command:`curl` command to retrieve a token:

    $ curl --include \
         --insecure \
         --request POST
         --data 'username=Administrator&password=s3cr3t' \
         https://FQDN/ucsschool-id-connector/api/token

.. _monitor-processing-status:

Monitor processing status
-------------------------

This section describes how to monitor the processing status of the |IDC| queues.
The status gives hints about how well the connector performs
and if it works as intended.

When users and groups change in UCS,
the |IDC| processes these changes as transactions
and synchronizes them to the connected |UAS| domains.
The connector puts the changes into queues
to increase the robustness of the connector
and to keep the load at a manageable level.

The |IDC| has an inbound queue that contains data
coming from the App Center listener converter.
The data uses a JSON representation of the changed objects.
The |IDC| transforms the data from the inbound queue
into transaction requests to the receiving systems.
It buffers each transaction in an outbound queue.
The |IDC| has one outbound queue per connected
school authority (|UAS| domain) for outbound data.

Each queue is a directory
and each transaction is a file in a queue directory.
The queues locate at the following directories:

Inbound queue
  :file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/listener`

Outbound queues
  :samp:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues/{queue_name}`

The |IDC| provides the resources ``/queues/``
and :samp:`/queues/{name}/`
that list the size of each queue.
With the resource :samp:`/queues/{name}/` you can query a distinct queue and
monitor it.
To retrieve the size of a queue, use the following steps:

#. Authenticate yourself with the API as described in :ref:`auth`.

#. Request the data from the |IDC| API.

.. _monitor-processing-status-example:

Example
~~~~~~~

The following example shows how to query the API for all queue lengths.
You can choose between a user interface approach with *Swagger UI*,
or a command-line approach.

.. tab:: Swagger UI

   Use the following steps with the Swagger UI:

   #. To authorize, click :guilabel:`Authorize`
      and enter the credentials of a legitimate user.

   #. In the *queues* section,
      open the *GET* ``/ucsschool-id-connector/api/v1/queues`` resource
      and click :guilabel:`Try it out`.

   #. Click the button :guilabel:`Execute`.
      In the *Server response* section,
      in the *Response body* area,
      you see a result similar to :numref:`monitor-processing-status-example-result`.

.. tab:: Command-line

   Use the following commands for the command line:

   #. Authorize yourself with the API and receive an ``access_token``:

      .. code-block:: console

         $ FQDN='<YOUR_FULLY_QUALIFIED_HOST_NAME>'
         $ curl \
               --include \
               --insecure \
               --request POST \
               --data 'username=Administrator&password=s3cr3t' \
               https://"$FQDN"/ucsschool-id-connector/api/token
         $ TOKEN='<YOUR_TOKEN>'

   #. Request a list of queues and use the ``access_token`` you retrieved
      before:

      .. code-block:: console

         $ curl \
               --insecure \
               --request 'GET' \
               'https://"$FQDN"/ucsschool-id-connector/api/v1/queues' \
               -H 'accept: application/json' \
               -H "Authorization: Bearer ${TOKEN}"

      You see a result similar to :numref:`monitor-processing-status-example-result`.

      .. hint::

         If you want to use a secure connection,
         you need download the UCS root certificate
         and pass it to :program:`curl`:

         .. code-block:: console

            $ F_PATH_CA_CERT="PATH_TO_UCS_ROOT_CERTIFICATE"
            $ curl \
                  --cacert "$F_PATH_CA_CERT" \
                  --request 'GET' \
                  'https://"$FQDN"/ucsschool-id-connector/api/v1/queues' \
                  -H 'accept: application/json' \
                  -H "Authorization: Bearer ${TOKEN}"


.. code-block:: json
   :caption: Example for a result
   :name: monitor-processing-status-example-result

   [
     {
       "name": "InQueue",
       "head": "",
       "length": 0,
       "school_authority": ""
     },
     {
       "name": "auth1",
       "head": "2024-01-11-13-43-36-196082_ready.json",
       "length": 2,
       "school_authority": "auth1"
     },
     {
       "name": "auth2",
       "head": "",
       "length": 0,
       "school_authority": "auth2"
     }
   ]

.. _monitor-processing-alerts:

Alerts for monitoring
~~~~~~~~~~~~~~~~~~~~~

If you want to add the |UAS| |IDC| to your monitoring environment
and let the monitoring send you alerts,
you may monitor the following problematic states.

Monotonous growth over a period of time
   If an |IDC| queue on the sending system grows continuously
   over a period of time,
   such as a day,
   the |IDC| isn't able to process transactions
   at the required speed as transactions arrive.
   Under normal circumstances, it may happen
   that the |IDC| can't process the transactions fast enough.
   If the queue sizes don't decrease at all for days,
   this could be a problem.

No change in queue size over a period of time
   If a queue size greater than ``0`` remains the same over a period of time,
   such as an hour,
   it indicates
   that the |IDC| isn't working
   or is stopping on corrupt transactions.
   If nothing changes in a queue and the size remains the same,
   you need to investigate.
   For more information, see :ref:`monitor-processing-interruption`.


Queues don't reach a size of ``0`` for a period of time
   If the queues don't run empty over a period of time,
   such as a week,
   this can mean that transactions are coming in at the same rate
   as the connector is processing them.
   Or, the |IDC| is running too slowly overall.
   Or, the target system may be unreachable due to
   network problems or incorrect configuration.

The amount of files located in the trash directory is rising continuously
   If the queues can't handle transactions because of internal errors,
   this can mean that the |KLV| API on the target system may be unreachable
   or the |KLV| API has an incorrect configuration.
   For more information, see :ref:`monitor-processing-interruption`.

.. hint::

   The right period of time to trigger an alarm
   depends on your specific environment.

.. _monitor-processing-interruption:

Interrupted processing
~~~~~~~~~~~~~~~~~~~~~~

If the queue processing doesn't go as planned,
for example,
because the service is unavailable,
the receiving system is unreachable,
the |IDC| app has crashed,
transactions are corrupt,
or for any other reason,
the queues grow in size or remain at a certain level.
If the |IDC| app service doesn't run,
the queues can quickly grow to a considerable size,
such as more than 1 million files after some days.

If a transaction has a valid JSON format,
but the receiver can't process it,
the |IDC| moves the JSON file with the transaction
from the queue to the :file:`trash` directory for the outgoing queue of the respective school authority located below
:file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues/{SCHOOL_AUTHORITY}`.
The value for :samp:`{SCHOOL_AUTHORITY}` reflects your respective school authority name.

The files located in the trash folder contain information that you can use to fix the issues.

#. You can use the DNs of the objects to find and fix the UDM objects:

   .. code-block:: console

      $ jq -r ".dn"  /var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues/SCHOOL_AUTHORITY/trash/*.json | sort | uniq

#. You can use the names of a ``TRANSACTION_FILE`` located in the :file:`trash` directory
   to find out which error the |IDC| raised and logged in the log file:

   .. code-block:: console

      $ grep -C 3 TRANSACTION_FILE /var/log/univention/ucsschool-id-connector/queues.log

You can re-schedule the objects after you fixed the issue.

* Reschedule a users:

  .. code-block:: console

     $ univention-app shell ucsschool-id-connector schedule_user USERNAME

* Reschedule a group:

  .. code-block:: console

     $ univention-app shell ucsschool-id-connector schedule_group GROUPNAME

* Reschedule a school and all associated objects:

  .. code-block:: console

     $ univention-app shell ucsschool-id-connector schedule_school SCHOOL

The |IDC| moves transactions with invalid or not accepted JSON formats
to the :file:`trash` directory for the outgoing queue of the respective school authority located below
:file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues/{SCHOOL_AUTHORITY}/`.

If a transaction in JSON format located in any queue is corrupt,
it may stay in the queue forever.
To resolve an interrupted queue, use the following steps:

#. Find out, which transaction is corrupt.

   Have a look at the queue log file
   of the |IDC| on the sending system at
   :file:`/var/log/univention/ucsschool-id-connector/queues.log`.

#. Resolve the error in the |IDC| setup.

   If other errors caused the corrupt transaction,
   you need to look at other parts.
   The |IDC| either logs a qualitative error happening on the sending system,
   or a generic error if a receiving system has an error with its |KLV| API.
   Review the configurations on the sending system and the receiving systems:

   * On the sending system, validate the configurations of school authority objects
     in the |UAS| |IDC|. Have a close look at the URL, credentials, and attribute mappings.

   * On the receiving systems, validate the attribute mapping
     and the incoming transactions through the |KLV| API.
     Have a look at the
     :external+uv-ucsschool-kelvin-rest-api:ref:`Kelvin log files <file locations>`.

   For information about watching the transaction processing,
   see :ref:`try-out`.

#. Remove the corrupt transaction from the queue.

   Use the transaction you found in the log file,
   find the JSON file that contains the transaction,
   and remove the JSON file.


.. _school-authorities-mapping:

School authorities mapping
--------------------------

You need to configure the following things:

1. The school authorities you want to send data to,
   and what data can they receive.
   This section describes the procedure.

2. The actual schools the receiving system handles, meaning the school authority.
   The following section: :ref:`School to authority mapping` describes the procedure.

Start with the first mapping, for school authorities.

To send user data to the target system,
you must decide which properties of which objects the system needs to send,
and more important, which properties **not** to send.

.. _phone-numbers-example:

For example, there might be telephone numbers for students in the system on the sending side,
but you don't want them available to the receiving school system.
Instead of forbidding properties,
you *map* properties on the sending side to properties on the receiving side.

.. _kelvin-config-example:

Here is what the mapping related part of an example configuration looks like:

.. code-block:: json

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

This configures a mapping for the |KLV| plugin that sends the three defined properties to the
receiving school:

* Synchronize the UDM ``ucsschoolRecordUID`` property to an |UAS| system as ``record_uid``.
* Synchronize the UDM ``ucsschoolSourceUID`` property to an |UAS| system as ``source_uid``.
* Synchronize the *virtual* ``roles`` property to an |UAS| system as ``roles``.

.. note::
   ``roles`` is *virtual* because there is special handling by the |UAS| |IDC| app
   mapping ``ucsschoolRole`` to ``roles``.

.. warning::

   When creating users through Kelvin, it requires some attributes.
   The following attributes must be present in the mapping:

   .. code-block:: json

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

  .. versionadded:: 3.1.0

    The following legal-guardian attributes are only allowed to be either configured both or not at all:

    .. code-block:: json

      {
        // ...
        "ucsschoolLegalGuardian": "legal_guardians",
        "ucsschoolLegalWard": "legal_wards"
      }

Here is a complete example that you can also find in the section  :ref:`school-authority-mapping`.

.. literalinclude:: ../examples/school_authority_kelvin.json
   :caption: Example of an ID Connector configuration for a school authority
   :language: json

.. _auth-config:

The mapping configuration uses the following keys:

``name``
   identifies a specific receiving system.
   It's a free-form string.
   Adapt to your needs and remember it.
   You need it in the next step.

``username`` and ``password``
   are the credentials that the receiving system needs.
   Use the
   :ref:`credentials you created when configuring the receiving system <kelvin_credentials>`.

``url``
   specifies the address of the receiving system.

``mapping``
   For a detailed description of the users' ``mapping`` inside
   ``plugin_configs["kelvin"]``, see :ref:`school-authorities-mapping`.

``school_classes``
   A mapping to setup the synchronization for school class groups.

``sync_password_hashes``
   Set to ``true``, if you want to synchronize the password hashes.

``ssl_context``
   contains the values that the connector passes to the :py:class:`ssl.SSLContext` object.
   The connector uses this object to communicate with the receiving system.

``active``
   set to ``true`` to activate the configuration for an out queue for a school authority.
   To deactivate the configuration, set the value to ``false``.

``plugins``
   Lists the plugins that the connector uses for this school authority.
   The list usually just has the element ``"kelvin"``.

Adapt the configuration to your needs.
You need to post the complete and adapted configuration
to the ``school_authorities`` resource using the :ref:`Swagger UI <swagger-ui>`.

.. _school-to-authority-map:

School to authority mapping
---------------------------

This section describes the second and last
:ref:`mapping <school-authorities-mapping>`
to setup the |UAS| ID Connector.

The before described mappings describe which school authorities you have.
This section describes how to map which school you want to synchronize to which authority.
A school authority can handle more than one school.
You therefore have a ``1:n`` mapping.

The format for the mapping is:

.. code-block:: json

   {
     "mapping": {
       "NAME_OF_SCHOOL": "NAME_OF_RECIPIENT",
       "ANOTHER_SCHOOL": "OTHER_OR_SAME_RECIPIENT"
      }
   }

You can have one or more schools in the mapping.

So assuming you have a ``DEMOSCHOOL`` on your sending system,
and you used the configuration before
to define ``Traeger1`` as a recipient system,
you could do:

.. code-block:: json

   {
     "mapping": {
       "DEMOSCHOOL": "Traeger1"
      }
   }

.. note::

   :ref:`Remember? <l10n>` ``Traeger`` refers to the receiving side of the synchronization process.

You also find this example in :ref:`school-to-authority-mapping`.

``PUT`` this configuration JSON to the ``school_to_authority_mapping`` resource
in the :ref:`Swagger UI<swagger-ui>`.

Role specific attribute mapping
-------------------------------

.. warning::

   This section describes an advanced scenario.
   If you don't explicitly need it, jump to the next section :ref:`try-out`.

Back to the :ref:`example about telephone numbers <phone-numbers-example>`.
Imagine you don't want to transfer telephone numbers for students,
you actually need them for teachers.
This means, that you need to define per role which properties you want to transfer.

.. versionadded:: 2.1.0

   The default |KLV| plugin version ``2.1.0`` received the role specific
   attribute mapping feature.
   This allows to define additional user mappings for each
   role such as ``student``, ``teacher``, ``staff``, ``legal_guardian`` and ``school_admin`` by adding a
   mapping next to the ``users`` mapping suffixed by ``_$ROLE``,
   for example ``users_student: {}``.

If the |KLV| plugin handles a user object,
the mapping looks like the following:

#. In the current school authority configuration, determine the schools that the authority handles.

#. Determine all roles the user has in these schools.

#. Order the roles by priority:

   * ``school_admin`` being the highest
   * ``staff``
   * ``teacher``
   * ``legal_guardian``
   * and then ``student`` with the lowest priority.

#. Find a ``users_$ROLE`` mapping from the ones configured in the plugin settings,
   pick the one with the highest priority.

#. If you couldn't fine any, fall back to the ``users`` mapping as the default.

.. _school-classes-problem-0:

You find an example for such a configuration in :ref:`role-specific-kelvin-plugin-mapping`.

.. note::

   The priority order for the roles aligns with the order of common specificity in |UAS|.

   A student only ever has the role ``student``.

   Teachers, staff, and school administrators can have multiple roles.

.. note::

   The mappings for the different roles aren't additive,
   because that approach would complicate the option to remove mappings from a specific role.
   Therefore, choose only *one* mapping by the rules just described.

.. _school-classes-problem-1:

.. warning::

   Users have the field ``school_classes``, which describes which school classes they belong to.
   You can prevent certain user roles from adding to or removing from school classes.

   Be aware that leaving out the ``school_classes`` from the mapping isn't sufficient to achieve this.
   Changing the school classes of a user doesn't only result in a user change event,
   but also a school class change event, which you need to handle separately.

   You therefore need to use a derivative of the |KLV| plugin, as described in :ref:`partial-group-sync`.

.. _partial-group-sync:

Partial group sync mapping
--------------------------

.. warning::

   This section describes an advanced scenario.
   If you don't explicitly need it, jump to the next section :ref:`try-out`.

Remember that in the last examples you had a property
that you would send for some users,
but not others,
depending on their role?
Turns out that you can have the same problem for groups.

Imagine that a school manages locally which teachers belong to which class.
In the role specific mapping you would **not** synchronize the classes attribute ``school_classes``,
to prevent overwriting the local managed settings, :ref:`see above <school-classes-problem-1>`.

This isn't enough though. You would also need to make sure
that you don't synchronize the property ``users`` of groups
which contains those teachers.

.. versionadded:: 2.1.0

   |KLV| plugin version ``2.1.0`` adds the derivative ``kelvin-partial-group-sync``.
   This plugin alters the handling of school class changes
   by allowing you to specify a list of roles that you want to ignore when
   synchronizing groups.

The following steps determine which members the connector sends to a school authority,
when an administrator adds a school class:

1. Add all users that are members of the school class locally.
   This is the default normal |KLV| plugin behavior.

2. Remove all users that have a configured role to ignore in any school
   handled by the school authority configuration.

3. Get all members of the school class on the target system that have one of the configured roles
   and add them.

4. Get all members of the school class on the target system that are unknown to the |IDC|
   and add them.

This results in school classes that have only members with roles not configured to ignore:

* members with roles to ignore that were added on the target system,
* any users added on the target system which are unknown to the |IDC|.

.. warning::

   To achieve this behavior, several additional LDAP queries on the |IDC|
   and one additional request to the target system are necessary.
   This affects performance.

To activate this alternative behavior,
replace the ``kelvin`` plugin in a school authority configuration with the ``kelvin-partial-group-sync`` plugin.
The configuration options are exactly the same as for the ``kelvin`` plugin,
except for the addition of ``school_classes_ignore_roles``,
which holds the list of user roles to ignore for school class changes.

For an example configuration, see :ref:`partial-groupsync`.

.. warning::

   Be aware that this plugin can only alter the handling of dedicated school class change events.
   Due to the technical situation, changing the members of a school class often results in two events:

   * a school class change
   * a user change

   To actually prevent the |IDC| to add users of certain roles to school classes at all,
   it's necessary to leave out the mapping of the users ``school_class`` field
   in the configuration as well - :ref:`see the previous section <school-classes-problem-0>`.

.. _try-out:

Trying it out
=============

Time has come to verify the setup.
In this section, you go through the following steps:

1. Create a test user.
2. Import the test user on the sending side.
3. Watch the synchronization of the test user to the receiving side.

.. caution::

   The |IDC| only synchronizes users with the properties ``ucsschoolRecordUID``
   and ``ucsschoolSourceUID``.
   You need to ensure that the user accounts used for testing have these properties.

The slow way is to
`create a user <https://help.univention.com/t/how-a-ucs-school-user-should-look-like/15630#a-sample-command-9>`_
individually and to ensure to amend the required properties,
or to use the |UAS| import.
For more information about user import in |UAS|,
see :cite:t:`uv-ucsschool-import`, German only.

With the fast way, you create and import the user in one step.
The following command creates a user within a class in the school ``DEMOSCHOOL``.

.. code-block:: bash

   $ /usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
     --students 1  --classes 1 DEMOSCHOOL

To see the synchronization action on the *sender system*,
you can watch the log file with the following command:

.. code-block:: bash

   $ tail -f /var/log/univention/ucsschool-id-connector/queues.log

To see the synchronization action on the *receiving system*,
you can watch the log file of |KLV| with the following command:

.. code-block:: bash

   $ tail -f /var/log/univention/ucsschool-kelvin-rest-api/http.log # kelvin log

You may need to wait a short moment before the queue picks up the created user.
If everything went fine,
you see some messages in the |KLV| log file on the receiving system.
You can confirm that the |IDC| created the user
in either the |KLV| web interface at :samp:`https://{FQDN}/ucsschool/kelvin/v1/docs`,
or in the UMC.

The following log files are also a good starting point for debugging in case something went wrong:

* On the sending system: :file:`/var/log/univention/ucsschool-id-connector/queues.log`

* On the receiving system: :file:`/var/log/univention/ucsschool-kelvin-rest-api/http.log`

.. important::

   During debugging, you must always ensure that the following is correct and matches:

   1. School authority configuration on the sender system,
      including authentication credentials.

   2. School to authority mapping on the sender system.

   3. :file:`mapped_udm_properties.json` on the receiving system has all extra attributes
      that are defined in the school authority mapping.


Starting / Stopping services
============================

Both services, |iIDCS| and  |iIDCH|, run in a Docker container.
You can start or stop the container by using the regular service facility of the UCS system:

.. code-block:: bash

    $ univention-app start ucsschool-id-connector
    $ univention-app status ucsschool-id-connector
    $ univention-app stop ucsschool-id-connector
    $ univention-app restart ucsschool-id-connector

Updates
=======

To install updates for |IDC|, use one of the two usual UCS ways.
Either through UMC or on the command line:

.. code-block:: console

    $ univention-app upgrade ucsschool-id-connector

Extra: setting up a second school authority
=============================================

If you already have a school authority set up
and you want to set up another one by copying its configuration,
you can do the following:

1. Make sure the school authority server that you want to add has the |KLV| app
   installed and running.

2. Retrieve the configuration for the old school authority.

   For this you open the HTTP-API Swagger UI at
   :samp:`https://{FQDN}/ucsschool-id-connector/api/v1/docs`
   and :ref:`authenticate yourself <authentication>`.

   To retrieve a list of the available school authorities,
   use the ``GET /ucsschool-id-connector/api/v1/school_authorities`` tab in the Swagger UI,
   click :guilabel:`Try it out` and :guilabel:`Execute`.

   In the response body, you receive a list of school authorities in JSON format,
   that the |IDC| has configured.
   You need to copy the school authority that you want to replicate and save it for later.

3. At the tab ``POST /ucsschool-id-connector/api/v1/school_authorities`` in the Swagger UI
   you can create the school authority.

   Click :guilabel:`Try it out` and insert the copied JSON object from before into the request body.

   **Before** you execute the request,
   you must alter the name, URL, and login credentials:

   * The URL must point to the school authority's |KLV| HTTP-API.
   * You can choose the name at your leisure.
   * The password is the authentication token of the school authority's HTTP-API that you retrieved earlier.

Use the tab :samp:`PATCH /ucsschool-id-connector/api/v1/school_authorities/{name}`
to change an already existing configuration.

To retrieve a list of the extended attributes on the old school authority server,
use the following command:

.. code-block:: bash

    $ udm settings/extended_attribute list
