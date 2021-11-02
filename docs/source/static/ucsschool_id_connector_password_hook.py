# -*- coding: utf-8 -*-

"""
UCS@school import hook to save password hashes sent by the UCS@school ID
Connector app.

Install it, by copying this file to /usr/share/ucs-school-import/pyhooks.
If the extended attribute to receive the password hashes is not called
`ucsschool_id_connector_pw`, change the name in the `PASSWORD_TARGET_ATTRIBUTE`
constant in line 18.
"""

import base64
import datetime

from ucsschool.importer.utils.user_pyhook import UserPyHook

PASSWORD_TARGET_ATTRIBUT = "ucsschool_id_connector_pw"  # nosec


class PasswordSync(UserPyHook):
    """
    Handle user.udm_properties[PASSWORD_TARGET_ATTRIBUT] that contains password
    hashes from the UCS@school ID Connector. Example:
    {
        'krb5KeyVersionNumber': 1,
        'userPassword': [u'{crypt}$6$icFo5bLKnDAvSoIq$2w...'],
        'sambaNTPassword': u'5C453F1961837BA114A045684F12FCF1',
        'sambaPwdLastSet': 1563801415,
        'krb5Key': ['TUVTaEt6QXBvQ...', 'TURTaEd6QVpvQU...', ...]
    }
    """

    priority = {
        "pre_create": 10000,
        "post_create": 10000,
        "pre_modify": 10000,
        "post_modify": 10000,
        "pre_move": None,
        "post_move": None,
        "pre_remove": None,
        "post_remove": None,
    }
    supports_dry_run = True
    password_hashes = {}

    def store_password_hashes(self, user):
        """
        Store PW hashes for post_create(), remove PASSWORD_TARGET_ATTRIBUT from
        `user.udm_properties`.
        """
        try:
            pw_hashes = user.udm_properties.pop(PASSWORD_TARGET_ATTRIBUT)
            self.logger.info("Password hashes found for user %s.", user.name)
        except KeyError:
            self.logger.warning("No password hashes found for user %s.", user.name)
            return
        if not isinstance(pw_hashes, dict):
            raise TypeError(
                "Value in attribute {!r} for user {!r} is not a dict.".format(
                    PASSWORD_TARGET_ATTRIBUT, user
                )
            )
        self.password_hashes[user.record_uid] = pw_hashes
        user.udm_properties["ucsschool_id_connector_last_update"] = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def set_hashes_in_ldap(self, user):
        """
        Store PW hashes in users LDAP object.
        """
        try:
            pw_hashes = self.password_hashes.pop(user.record_uid)
        except KeyError:
            self.logger.warning("No password hashes found for user %s.", user.name)
            return
        if not isinstance(pw_hashes, dict):
            raise TypeError("Value of cached password_hashes for user {!r} is not a dict.".format(user))
        ml = []
        old_data = self.lo.get(user.dn, attr=map(str, pw_hashes.keys()))  # no unicode
        for key, value in pw_hashes.items():
            if key in ("krb5KeyVersionNumber", "sambaPwdLastSet"):
                value = str(value)  # int 2 str for happy lo.modify()
            elif key == "krb5Key":
                value = [base64.b64decode(krb5Key.encode("ascii")) for krb5Key in value]
            value = value if isinstance(value, list) else [value]
            if not set(value).issubset(set(old_data.get(key, []))):
                ml.append((key, old_data.get(key, []), value))
        if self.dry_run:
            self.logger.info("(dry-run) would now set password hashes for user %s.", user.name)
        elif not ml:
            self.logger.info("Passwords unchanged for user %s.", user.name)
        else:
            self.lo.modify(user.dn, ml)
            self.logger.info("Updated passwords of user %s.", user.name)

    pre_create = store_password_hashes
    post_create = set_hashes_in_ldap
    pre_modify = store_password_hashes
    post_modify = set_hashes_in_ldap
