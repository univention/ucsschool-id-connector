.. Please add a line break after each sentence.
.. This will reduce the diff when changing text.

===========================================
Multi-scenario support for the M2M-sync app
===========================================

The Master to Master synchronization app has to be adaptable to different scenarios.
Where possible it should be done through the configuration (using the HTTP-API).
If specialized code is required, then hooks/plugins/extensions must be used.

This document describes all extension points that can be used to individualise the Master to Master synchronization app.

Extension points for MV vs. SH
------------------------------
Common code for the two project is kept directly in the app.
Differences are either configurable (also common code) or moved into plugins.

Detection: object type
^^^^^^^^^^^^^^^^^^^^^^

In MV only users are synchronized.
They are common UDM ``users/user`` objects (UCS\@school is not installed).
There are two types of users: students and teachers.
They can be differentiated through the property ``mvStaffType``.
Two or three values are possible: ``Lehrer`` (verified), ``Schueler`` (not yet verified) and a unknown string for staff members.

In SH users and groups are synchronized.
They have UCS\@school installed and the object types of users can thus be detected through the ``objectClass`` (or in our case with the UDM ``options`` list).
The groups must be separated into ``SchoolClass`` and ``Workgroup`` objects.
Currently that can only be done in two ways: a) by analysing the name:
School class names have a ``$OU`` *prefix* and work group names have a ``$OU`` *postfix*.
The ``OU`` can be found by dissecting the objects ``position``, b) by using the ``ucsschool_role`` property.

Different code will be required when loading and validating listener files and when starting a work flow depending on the object type.
Those differences will be in the ``Model`` classes, in the ``distribute()`` method and in the out queue handler.

Listener file preprocessing (in queue)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When the in queue discovers a new file dropped of by the listener, it does some processing on it, before copying it to the respective out queues.
That includes validating the file content, loading (or storing) data missing (or found) in the file etc.

What happens here is very project specific.
An extension point is required in the method ``mv_idm_gw.queues.InQueue.preprocess_file()``.

Out queue selection (in queue)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before user/group objects can be updated on the target systems, it has to be decided *which* systems have to be contacted.
For MV and SH this is done differently:

In MV all school authorities a user is a member of, are listed in the ``mvDst`` attribute.
The name used in the ``mvDst`` attribute is the same as the name of a ``SchoolAuthorityConfiguration`` object.

In SH users and groups are UCS\@school objects.
As such their membership can be read directly from the ``school`` and/or ``schools`` attributes.
It is currently planned that the SH system will have a mapping from school names to school authorities.

The method of deciding which school authority servers to contact is project specific.
The information is required in ``mv_idm_gw.queues.InQueue.distribute()``.
An extension point is required there.

Out queue handler
^^^^^^^^^^^^^^^^^

At the moment most of the code for sending (creating/updating/deleting) the users current state to a target system (school authority) is in the ``mv_idm_gw.user_handler.UserHandler`` class.
Each out queue has a ``UserHandler`` object attached, configured for its specific school authority.
The ``UserHandler`` object does both the mapping of the UDM objects properties to a HTTP-API resource (including special handling for a number of properties) and the actual API calls.

The handler class should be rewritten to a framework style pipe.
The first stage would be to transform the UDM object to a HTTP-API resource and the second stage the actual HTTP requests.

The differences in the first stage for users will be mostly the handling of special properties.

For SH an additional ``Grouphandler`` (or maybe two, for *school classes* and *work groups*) will be required.
This will only be possible when after switching to the Kelvin-API, as the BB-API does not support managing groups.

The second stage will differ only when switching from the BB-API to the Kelvin-API.
I don't think that handling users and groups will make a difference here.

Time related actions
^^^^^^^^^^^^^^^^^^^^

In MV all memberships (for school classes, schools, main school and school authorities) have time constraints.
As memberships start and end without modifications to the user object, a separate process scnas for those events and schedules appropriate actions.
The process is implemented as a cron job that runs each day and executes the ``schedule_mvdst_events`` script.
It searches the LDAP for users with starting or ending memberships, and creates a app center listener file in the in queue.

In SH no such process is required.
All membership modifications are performed on the upstream system.
Those changes will arrive in the UCS system with the next import, triggering the app center listener to create a file in the in queue.

Models
^^^^^^

The classes in the ``mv_idm_gw.models`` module are the foundation of all data passing happening in the queueing system and the HTTP-API.
They have been written for the MV project and some have to be adapted.

* ``ListenerAddModifyObject``: Python representation of a JSON dump made by the listener.

  * It currently has an attribute ``user_passwords`` (of type ``UserPasswords``) that contains the password hashes of the user currently being created/modified. That will be required in both projects, but as in SH also groups will be synchronized it must be moved to a subclass for user objects or must be associated more loosely.
  * The property ``role`` should return the UCS\@school role (``staff``, ``student`` or ``teacher``). How the role is determined is is dofferent in MV (from property ``mvStaffType``) and SH (from UCS\@school ``roles`` property or UDM objects ``options``).
* ``SchoolAuthorityConfiguration``: Configuration of a target system (property mapping, URL, token etc).
* ``SchoolAuthorityConfigurationPatchDocument``: Same as ``SchoolAuthorityConfiguration`` but with all attributes marked as optional.
* ``ListenerOldDataEntry``: Container used to store data in the "old database" - required only in MV.
* The SH project will require a model to create, update and store the school to school authority mapping.

HTTP monitoring and management API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The SH project will require an additional resource to create, retrieve and update the school to school authority mapping plus a matching RPC method.

All differences listed in the *Models* section have the potential to require modifications to the HTTP API (and the accompanying RPC methods).

Tests
^^^^^

There will be tests for common code and tests for project specifics.
The common tests will kept in a ``tests`` directory besides the ``mv_idm_gw`` (to be renamed) package.
Project specific tests should be stored together with the plugins in the same directory.
The name of all files (modules) containing tests must start with ``test_``.


Extension points for BB-API vs. Kelvin-API
------------------------------------------

Authorization at target systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

BB-API
""""""
* HTTP header: ``'Authorization': 'Token s3cr3t'``
* Token stays valid forever
* Token must be retrieved manually (no HTTP resource available).

Kelvin-API
""""""""""
* HTTP header: ``'Authorization': 'Token s3cr3t'``
* Token expires after 60 minutes (configurable).
* Access ist only granted to members of the group ``kelvin-users``.
* Has to be retrieved using a dedicated resource.

Token retrieval example::

    $ curl -i -k -X POST --data 'username=Administrator&password=s3cr3t' https://FQDN/kelvin/api/token
