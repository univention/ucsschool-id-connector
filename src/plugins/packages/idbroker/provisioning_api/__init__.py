# coding: utf-8

# flake8: noqa

"""
    UCS@school APIs

    This application exposes network resources introduced via custom plugins.  # noqa: E501

    The version of the OpenAPI document: 0.1.0
    Generated by: https://openapi-generator.tech
"""


from __future__ import absolute_import

__version__ = "1.0.0"

# import apis into sdk package
from idbroker.provisioning_api.api.auth_api import AuthApi
from idbroker.provisioning_api.api.provisioning_api import ProvisioningApi
from idbroker.provisioning_api.api.school_classes_api import SchoolClassesApi
from idbroker.provisioning_api.api.schools_api import SchoolsApi
from idbroker.provisioning_api.api.users_api import UsersApi

# import ApiClient
from idbroker.provisioning_api.api_client import ApiClient
from idbroker.provisioning_api.configuration import Configuration
from idbroker.provisioning_api.exceptions import OpenApiException
from idbroker.provisioning_api.exceptions import ApiTypeError
from idbroker.provisioning_api.exceptions import ApiValueError
from idbroker.provisioning_api.exceptions import ApiKeyError
from idbroker.provisioning_api.exceptions import ApiAttributeError
from idbroker.provisioning_api.exceptions import ApiException
# import models into sdk package
from idbroker.provisioning_api.models.http_validation_error import HTTPValidationError
from idbroker.provisioning_api.models.school import School
from idbroker.provisioning_api.models.school_class import SchoolClass
from idbroker.provisioning_api.models.school_context import SchoolContext
from idbroker.provisioning_api.models.token import Token
from idbroker.provisioning_api.models.user import User
from idbroker.provisioning_api.models.validation_error import ValidationError
