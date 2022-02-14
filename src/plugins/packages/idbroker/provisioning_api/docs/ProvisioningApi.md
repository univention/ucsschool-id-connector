# idbroker.provisioning_api.ProvisioningApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**delete_ucsschool_apis_provisioning_v1_school_authority_classes_id_delete**](ProvisioningApi.md#delete_ucsschool_apis_provisioning_v1_school_authority_classes_id_delete) | **DELETE** /ucsschool/apis/provisioning/v1/{school_authority}/classes/{id} | Delete
[**delete_ucsschool_apis_provisioning_v1_school_authority_users_id_delete**](ProvisioningApi.md#delete_ucsschool_apis_provisioning_v1_school_authority_users_id_delete) | **DELETE** /ucsschool/apis/provisioning/v1/{school_authority}/users/{id} | Delete
[**get_head_ucsschool_apis_provisioning_v1_school_authority_classes_id_head**](ProvisioningApi.md#get_head_ucsschool_apis_provisioning_v1_school_authority_classes_id_head) | **HEAD** /ucsschool/apis/provisioning/v1/{school_authority}/classes/{id} | Get Head
[**get_head_ucsschool_apis_provisioning_v1_school_authority_schools_id_head**](ProvisioningApi.md#get_head_ucsschool_apis_provisioning_v1_school_authority_schools_id_head) | **HEAD** /ucsschool/apis/provisioning/v1/{school_authority}/schools/{id} | Get Head
[**get_head_ucsschool_apis_provisioning_v1_school_authority_users_id_head**](ProvisioningApi.md#get_head_ucsschool_apis_provisioning_v1_school_authority_users_id_head) | **HEAD** /ucsschool/apis/provisioning/v1/{school_authority}/users/{id} | Get Head
[**get_ucsschool_apis_provisioning_v1_school_authority_classes_id_get**](ProvisioningApi.md#get_ucsschool_apis_provisioning_v1_school_authority_classes_id_get) | **GET** /ucsschool/apis/provisioning/v1/{school_authority}/classes/{id} | Get
[**get_ucsschool_apis_provisioning_v1_school_authority_schools_id_get**](ProvisioningApi.md#get_ucsschool_apis_provisioning_v1_school_authority_schools_id_get) | **GET** /ucsschool/apis/provisioning/v1/{school_authority}/schools/{id} | Get
[**get_ucsschool_apis_provisioning_v1_school_authority_users_id_get**](ProvisioningApi.md#get_ucsschool_apis_provisioning_v1_school_authority_users_id_get) | **GET** /ucsschool/apis/provisioning/v1/{school_authority}/users/{id} | Get
[**post_ucsschool_apis_provisioning_v1_school_authority_classes_post**](ProvisioningApi.md#post_ucsschool_apis_provisioning_v1_school_authority_classes_post) | **POST** /ucsschool/apis/provisioning/v1/{school_authority}/classes | Post
[**post_ucsschool_apis_provisioning_v1_school_authority_schools_post**](ProvisioningApi.md#post_ucsschool_apis_provisioning_v1_school_authority_schools_post) | **POST** /ucsschool/apis/provisioning/v1/{school_authority}/schools | Post
[**post_ucsschool_apis_provisioning_v1_school_authority_users_post**](ProvisioningApi.md#post_ucsschool_apis_provisioning_v1_school_authority_users_post) | **POST** /ucsschool/apis/provisioning/v1/{school_authority}/users | Post
[**put_ucsschool_apis_provisioning_v1_school_authority_classes_id_put**](ProvisioningApi.md#put_ucsschool_apis_provisioning_v1_school_authority_classes_id_put) | **PUT** /ucsschool/apis/provisioning/v1/{school_authority}/classes/{id} | Put
[**put_ucsschool_apis_provisioning_v1_school_authority_users_id_put**](ProvisioningApi.md#put_ucsschool_apis_provisioning_v1_school_authority_users_id_put) | **PUT** /ucsschool/apis/provisioning/v1/{school_authority}/users/{id} | Put


# **delete_ucsschool_apis_provisioning_v1_school_authority_classes_id_delete**
> delete_ucsschool_apis_provisioning_v1_school_authority_classes_id_delete(id, school_authority)

Delete

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Delete
        api_instance.delete_ucsschool_apis_provisioning_v1_school_authority_classes_id_delete(id, school_authority)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->delete_ucsschool_apis_provisioning_v1_school_authority_classes_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

void (empty response body)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_ucsschool_apis_provisioning_v1_school_authority_users_id_delete**
> delete_ucsschool_apis_provisioning_v1_school_authority_users_id_delete(id, school_authority)

Delete

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Delete
        api_instance.delete_ucsschool_apis_provisioning_v1_school_authority_users_id_delete(id, school_authority)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->delete_ucsschool_apis_provisioning_v1_school_authority_users_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

void (empty response body)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_head_ucsschool_apis_provisioning_v1_school_authority_classes_id_head**
> object get_head_ucsschool_apis_provisioning_v1_school_authority_classes_id_head(id, school_authority)

Get Head

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Get Head
        api_response = api_instance.get_head_ucsschool_apis_provisioning_v1_school_authority_classes_id_head(id, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->get_head_ucsschool_apis_provisioning_v1_school_authority_classes_id_head: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

**object**

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_head_ucsschool_apis_provisioning_v1_school_authority_schools_id_head**
> object get_head_ucsschool_apis_provisioning_v1_school_authority_schools_id_head(id, school_authority)

Get Head

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Get Head
        api_response = api_instance.get_head_ucsschool_apis_provisioning_v1_school_authority_schools_id_head(id, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->get_head_ucsschool_apis_provisioning_v1_school_authority_schools_id_head: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

**object**

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_head_ucsschool_apis_provisioning_v1_school_authority_users_id_head**
> object get_head_ucsschool_apis_provisioning_v1_school_authority_users_id_head(id, school_authority)

Get Head

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Get Head
        api_response = api_instance.get_head_ucsschool_apis_provisioning_v1_school_authority_users_id_head(id, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->get_head_ucsschool_apis_provisioning_v1_school_authority_users_id_head: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

**object**

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_ucsschool_apis_provisioning_v1_school_authority_classes_id_get**
> SchoolClass get_ucsschool_apis_provisioning_v1_school_authority_classes_id_get(id, school_authority)

Get

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Get
        api_response = api_instance.get_ucsschool_apis_provisioning_v1_school_authority_classes_id_get(id, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->get_ucsschool_apis_provisioning_v1_school_authority_classes_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

[**SchoolClass**](SchoolClass.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_ucsschool_apis_provisioning_v1_school_authority_schools_id_get**
> School get_ucsschool_apis_provisioning_v1_school_authority_schools_id_get(id, school_authority)

Get

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Get
        api_response = api_instance.get_ucsschool_apis_provisioning_v1_school_authority_schools_id_get(id, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->get_ucsschool_apis_provisioning_v1_school_authority_schools_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

[**School**](School.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_ucsschool_apis_provisioning_v1_school_authority_users_id_get**
> User get_ucsschool_apis_provisioning_v1_school_authority_users_id_get(id, school_authority)

Get

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.

    try:
        # Get
        api_response = api_instance.get_ucsschool_apis_provisioning_v1_school_authority_users_id_get(id, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->get_ucsschool_apis_provisioning_v1_school_authority_users_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 

### Return type

[**User**](User.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **post_ucsschool_apis_provisioning_v1_school_authority_classes_post**
> SchoolClass post_ucsschool_apis_provisioning_v1_school_authority_classes_post(school_authority, school_class)

Post

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.
school_class = idbroker.provisioning_api.SchoolClass() # SchoolClass | 

    try:
        # Post
        api_response = api_instance.post_ucsschool_apis_provisioning_v1_school_authority_classes_post(school_authority, school_class)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->post_ucsschool_apis_provisioning_v1_school_authority_classes_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 
 **school_class** | [**SchoolClass**](SchoolClass.md)|  | 

### Return type

[**SchoolClass**](SchoolClass.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **post_ucsschool_apis_provisioning_v1_school_authority_schools_post**
> School post_ucsschool_apis_provisioning_v1_school_authority_schools_post(school_authority, school)

Post

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.
school = idbroker.provisioning_api.School() # School | 

    try:
        # Post
        api_response = api_instance.post_ucsschool_apis_provisioning_v1_school_authority_schools_post(school_authority, school)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->post_ucsschool_apis_provisioning_v1_school_authority_schools_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 
 **school** | [**School**](School.md)|  | 

### Return type

[**School**](School.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **post_ucsschool_apis_provisioning_v1_school_authority_users_post**
> User post_ucsschool_apis_provisioning_v1_school_authority_users_post(school_authority, user)

Post

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.
user = idbroker.provisioning_api.User() # User | 

    try:
        # Post
        api_response = api_instance.post_ucsschool_apis_provisioning_v1_school_authority_users_post(school_authority, user)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->post_ucsschool_apis_provisioning_v1_school_authority_users_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 
 **user** | [**User**](User.md)|  | 

### Return type

[**User**](User.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **put_ucsschool_apis_provisioning_v1_school_authority_classes_id_put**
> SchoolClass put_ucsschool_apis_provisioning_v1_school_authority_classes_id_put(id, school_authority, school_class)

Put

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.
school_class = idbroker.provisioning_api.SchoolClass() # SchoolClass | 

    try:
        # Put
        api_response = api_instance.put_ucsschool_apis_provisioning_v1_school_authority_classes_id_put(id, school_authority, school_class)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->put_ucsschool_apis_provisioning_v1_school_authority_classes_id_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 
 **school_class** | [**SchoolClass**](SchoolClass.md)|  | 

### Return type

[**SchoolClass**](SchoolClass.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **put_ucsschool_apis_provisioning_v1_school_authority_users_id_put**
> User put_ucsschool_apis_provisioning_v1_school_authority_users_id_put(id, school_authority, user)

Put

### Example

* OAuth Authentication (OAuth2PasswordBearer):
```python
from __future__ import print_function
import time
import idbroker.provisioning_api
from idbroker.provisioning_api.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: OAuth2PasswordBearer
configuration = idbroker.provisioning_api.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.ProvisioningApi(api_client)
    id = 'id_example' # str | Unique ID of LDAP object on school authority side.
school_authority = 'school_authority_example' # str | Identifier of the school authority this object originates from.
user = idbroker.provisioning_api.User() # User | 

    try:
        # Put
        api_response = api_instance.put_ucsschool_apis_provisioning_v1_school_authority_users_id_put(id, school_authority, user)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling ProvisioningApi->put_ucsschool_apis_provisioning_v1_school_authority_users_id_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **id** | **str**| Unique ID of LDAP object on school authority side. | 
 **school_authority** | **str**| Identifier of the school authority this object originates from. | 
 **user** | [**User**](User.md)|  | 

### Return type

[**User**](User.md)

### Authorization

[OAuth2PasswordBearer](../README.md#OAuth2PasswordBearer)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

