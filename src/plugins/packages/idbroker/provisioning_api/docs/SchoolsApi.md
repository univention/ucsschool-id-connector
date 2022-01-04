# idbroker.provisioning_api.SchoolsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_head_ucsschool_apis_provisioning_v1_school_authority_schools_name_head**](SchoolsApi.md#get_head_ucsschool_apis_provisioning_v1_school_authority_schools_name_head) | **HEAD** /ucsschool/apis/provisioning/v1/{school_authority}/schools/{name} | Get Head
[**get_ucsschool_apis_provisioning_v1_school_authority_schools_name_get**](SchoolsApi.md#get_ucsschool_apis_provisioning_v1_school_authority_schools_name_get) | **GET** /ucsschool/apis/provisioning/v1/{school_authority}/schools/{name} | Get
[**post_ucsschool_apis_provisioning_v1_school_authority_schools_post**](SchoolsApi.md#post_ucsschool_apis_provisioning_v1_school_authority_schools_post) | **POST** /ucsschool/apis/provisioning/v1/{school_authority}/schools | Post


# **get_head_ucsschool_apis_provisioning_v1_school_authority_schools_name_head**
> object get_head_ucsschool_apis_provisioning_v1_school_authority_schools_name_head(name, school_authority)

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
    api_instance = idbroker.provisioning_api.SchoolsApi(api_client)
    name = 'name_example' # str | 
school_authority = 'school_authority_example' # str | 

    try:
        # Get Head
        api_response = api_instance.get_head_ucsschool_apis_provisioning_v1_school_authority_schools_name_head(name, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling SchoolsApi->get_head_ucsschool_apis_provisioning_v1_school_authority_schools_name_head: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 
 **school_authority** | **str**|  | 

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

# **get_ucsschool_apis_provisioning_v1_school_authority_schools_name_get**
> School get_ucsschool_apis_provisioning_v1_school_authority_schools_name_get(name, school_authority)

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
    api_instance = idbroker.provisioning_api.SchoolsApi(api_client)
    name = 'name_example' # str | 
school_authority = 'school_authority_example' # str | 

    try:
        # Get
        api_response = api_instance.get_ucsschool_apis_provisioning_v1_school_authority_schools_name_get(name, school_authority)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling SchoolsApi->get_ucsschool_apis_provisioning_v1_school_authority_schools_name_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **name** | **str**|  | 
 **school_authority** | **str**|  | 

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
    api_instance = idbroker.provisioning_api.SchoolsApi(api_client)
    school_authority = 'school_authority_example' # str | 
school = idbroker.provisioning_api.School() # School | 

    try:
        # Post
        api_response = api_instance.post_ucsschool_apis_provisioning_v1_school_authority_schools_post(school_authority, school)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling SchoolsApi->post_ucsschool_apis_provisioning_v1_school_authority_schools_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **school_authority** | **str**|  | 
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

