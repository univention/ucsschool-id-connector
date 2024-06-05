# -*- coding: utf-8 -*-

# Copyright 2019-2020 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import copy
import logging
import os
import time
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest
from faker import Faker

import ucsschool_id_connector.utils

fake = Faker()

DN_REGEX = {
    "domain_users_ou_dn_regex": "cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,{ldap_base}",
    "lehrer_ou_dn_regex": "cn=lehrer-demoschool,cn=groups,ou=DEMOSCHOOL,{ldap_base}",
    "schueler_ou_dn_regex": "cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,{ldap_base}",
    "school_class_dn_regex": "cn=DEMOSCHOOL-1a,cn=klassen,cn=schueler,cn=groups,ou=DEMOSCHOOL,"
    "{ldap_base}",
    "student_dn_regex": "uid=demo_student,cn=schueler,cn=users,ou=DEMOSCHOOL,{ldap_base}",
    "teacher_dn_regex": "uid=demo_teacher,cn=lehrer,cn=users,ou=DEMOSCHOOL,{ldap_base}",
    "teacher_and_staff_dn_regex": "uid=demo_teachstaff,cn=lehrer und mitarbeiter,cn=users,ou=DEMOSCHOOL,"
    "{ldap_base}",
    "workgroup_dn_regex": "cn=DEMOSCHOOL-wg1,cn=schueler,cn=groups,ou=DEMOSCHOOL,{ldap_base}",
}


@pytest.fixture
def ldap_base(setup_environ) -> str:
    return os.environ["ldap_base"]


def test_get_ucrv_unknown_key_no_default(temp_file_func):
    ucr_file = temp_file_func()
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file):
        value = ucsschool_id_connector.utils.get_ucrv(fake.pystr())
    assert value is None


def test_get_ucrv_unknown_key_with_default(temp_file_func):
    ucr_file = temp_file_func()
    exp_val = fake.pystr()
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file):
        value = ucsschool_id_connector.utils.get_ucrv(fake.pystr(), exp_val)
    assert value is exp_val


def test_get_ucrv_known_key(temp_file_func):
    ucr_file = temp_file_func()
    key, exp_val = fake.pystr(), fake.pystr()
    with open(ucr_file, "w") as fp:
        fp.write(f"{key}: {exp_val}")
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file):
        value = ucsschool_id_connector.utils.get_ucrv(key)
    assert value == exp_val


def test_get_ucrv_stale_cache(temp_file_func):
    ucr_file = temp_file_func()
    key, exp_val1, exp_val2 = fake.pystr(), fake.pystr(), fake.pystr()
    with open(ucr_file, "w") as fp:
        fp.write(f"{key}: {exp_val1}")
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file):
        value = ucsschool_id_connector.utils.get_ucrv(key)
        assert value == exp_val1
        time.sleep(0.01)
        with open(ucr_file, "w") as fp:
            fp.write(f"{key}: {exp_val2}")
        value = ucsschool_id_connector.utils.get_ucrv(key)
        assert value == exp_val2


def test_get_ucrv_no_base_conf_file():
    ucr_file = f"/tmp/non-exist-{fake.pystr()}"
    default_value = fake.pystr()
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file):
        value = ucsschool_id_connector.utils.get_ucrv(fake.pystr(), default_value)
        assert value is default_value


@pytest.mark.parametrize(
    "val,exp_val",
    (
        (fake.pystr(), logging.INFO),
        ("", logging.INFO),
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
    ),
)
def test_get_log_level(tmp_path_factory, val, exp_val):
    default = logging.INFO
    etc_ucr = tmp_path_factory.mktemp("ucr")
    ucr_file = etc_ucr / "base.conf"
    ucr_file.touch()
    ucr_key = "ucsschool-id-connector/log_level"
    ucsschool_id_connector.utils._get_ucrv_cached.cache_clear()
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file):
        value = ucsschool_id_connector.utils.get_log_level()
        assert value == default
        time.sleep(0.01)
        with open(ucr_file, "w") as fp:
            fp.write(f"{ucr_key}: {val}")
        ucsschool_id_connector.utils._get_ucrv_cached.cache_clear()
        value = ucsschool_id_connector.utils.get_log_level()
        assert value == exp_val


def test_get_token_ttl(temp_file_func):
    ucr_file = temp_file_func()
    key, default, exp_val = fake.pystr(), str(fake.pyint()), str(fake.pyint())
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file), patch(
        "ucsschool_id_connector.utils.UCRV_TOKEN_TTL", (key, default)
    ):
        value = ucsschool_id_connector.utils.get_token_ttl()
        assert value == int(default)
        time.sleep(0.01)
        with open(ucr_file, "w") as fp:
            fp.write(f"{key}: {exp_val}")
        value = ucsschool_id_connector.utils.get_token_ttl()
        assert value == int(exp_val)


def test_get_source_uid(temp_file_func):
    ucr_file = temp_file_func()
    key, default, exp_val = fake.pystr(), fake.pystr(), fake.pystr()
    with patch("ucsschool_id_connector.utils.UCR_DB_FILE", ucr_file), patch(
        "ucsschool_id_connector.utils.UCRV_SOURCE_UID", (key, default)
    ):
        value = ucsschool_id_connector.utils.get_source_uid()
        assert value == default
        time.sleep(0.01)
        with open(ucr_file, "w") as fp:
            fp.write(f"{key}: {exp_val}")
        value = ucsschool_id_connector.utils.get_source_uid()
        assert value == exp_val


def regex_dn_id(value) -> str:
    return value[0]


@pytest.mark.parametrize("regex_dn", DN_REGEX.items(), ids=regex_dn_id)
def test_dn_regex_exact_matches(regex_dn, ldap_base):
    correct_regex_func, dn = regex_dn
    dn = dn.format(ldap_base=ldap_base)
    for current_regex_func in DN_REGEX.keys():
        func = getattr(ucsschool_id_connector.utils, current_regex_func)
        regex = func()
        if current_regex_func == correct_regex_func:
            assert regex.match(dn)
        else:
            assert not regex.match(dn)


def test_entry_uuid_to_base58_to_entry_uuid():
    uuid_s = fake.uuid4(cast_to=str)
    uuid_as_b58 = ucsschool_id_connector.utils.entry_uuid_to_base58(uuid_s)
    assert ucsschool_id_connector.utils.base58_to_entry_uuid(uuid_as_b58) == uuid_s


def test_recursive_dict_update():
    ori = {
        "a": "A",
        "b": "B",
        "c": ["C"],
        "d": {
            1: 2,
            None: 3,
            "4": 5,
        },
        "e": None,
        "f": {"g": {"h": "H", "i": "I"}},
    }
    updater = {}
    assert ucsschool_id_connector.utils.recursive_dict_update(ori, updater) == ori

    updater = {"a": "X", "k": "K"}
    result = copy.deepcopy(ori)
    result["a"] = "X"
    result["k"] = "K"
    assert ucsschool_id_connector.utils.recursive_dict_update(ori, updater) == result

    updater["d"] = {1: 4}
    result["d"] = {
        1: 4,
        None: 3,
        "4": 5,
    }
    assert ucsschool_id_connector.utils.recursive_dict_update(result, updater) == result
    updater["f"] = {"g": {"h": "HAHA"}}
    result["f"] = {"g": {"h": "HAHA", "i": "I"}}
    assert ucsschool_id_connector.utils.recursive_dict_update(result, updater) == result

    unchanged_result = copy.deepcopy(result)
    updater["f"] = "boom"
    with pytest.raises(ValueError):
        ucsschool_id_connector.utils.recursive_dict_update(result, updater)
    assert result == unchanged_result

    updater["f"] = {"g": "boom"}
    with pytest.raises(ValueError):
        ucsschool_id_connector.utils.recursive_dict_update(result, updater)
    assert result == unchanged_result


def test_recursive_dict_update_only_changed():
    my_updater = {"plugin_configs": {"id_broker": {"schools": ["ou2"]}}}

    my_ori = {
        "name": "Traeger2",
        "active": True,
        "url": "https://provisioning1.broker.test/",
        "plugins": ["id_broker-users", "id_broker-groups"],
        "plugin_configs": {
            "id_broker": {
                "password": "mypassword",
                "schools": [],
                "username": "provisioning-Traeger2",
                "version": 1,
            }
        },
    }
    for key in my_ori:
        if key not in my_updater:
            my_updater[key] = None
    my_updater["plugin_configs"]["id_broker"]["version"] = None
    my_updater["plugin_configs"]["id_broker"]["username"] = None
    my_updater["plugin_configs"]["id_broker"]["password"] = None
    res = ucsschool_id_connector.utils.recursive_dict_update(
        ori=my_ori, updater=my_updater, update_none_values=False
    )
    assert res == {
        "name": "Traeger2",
        "active": True,
        "url": "https://provisioning1.broker.test/",
        "plugins": ["id_broker-users", "id_broker-groups"],
        "plugin_configs": {
            "id_broker": {
                "password": "mypassword",
                "schools": ["ou2"],
                "username": "provisioning-Traeger2",
                "version": 1,
            }
        },
    }


def test_get_version():
    get_app_version_result = ucsschool_id_connector.utils.get_app_version()
    src_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    app_path = Path("/ucsschool-id-connector/src/pyproject.toml")
    for path in (src_path, app_path):
        try:
            with open(path, "rb") as fp:
                version_from_file = tomllib.load(fp)["tool"]["poetry"]["version"]
            break
        except IOError:
            pass
    else:
        raise RuntimeError(f"Could not find 'pyproject.toml' in {src_path!s} or {app_path!s}.")
    assert version_from_file == get_app_version_result
