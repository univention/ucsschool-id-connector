# idbroker.provisioning_api.AuthApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**login_for_access_token_ucsschool_apis_auth_token_post**](AuthApi.md#login_for_access_token_ucsschool_apis_auth_token_post) | **POST** /ucsschool/apis/auth/token | Login For Access Token


# **login_for_access_token_ucsschool_apis_auth_token_post**
> Token login_for_access_token_ucsschool_apis_auth_token_post(username, password, grant_type=grant_type, scope=scope, client_id=client_id, client_secret=client_secret)

Login For Access Token

This route enables LDAP bind authentication against the apps host UCS system. :param form_data: The login credentials (username, password) :return: If login successful, the JWT data.

### Example

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


# Enter a context with an instance of the API client
with idbroker.provisioning_api.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = idbroker.provisioning_api.AuthApi(api_client)
    username = 'username_example' # str | 
password = 'password_example' # str | 
grant_type = 'grant_type_example' # str |  (optional)
scope = '' # str |  (optional) (default to '')
client_id = 'client_id_example' # str |  (optional)
client_secret = 'client_secret_example' # str |  (optional)

    try:
        # Login For Access Token
        api_response = api_instance.login_for_access_token_ucsschool_apis_auth_token_post(username, password, grant_type=grant_type, scope=scope, client_id=client_id, client_secret=client_secret)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling AuthApi->login_for_access_token_ucsschool_apis_auth_token_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **username** | **str**|  | 
 **password** | **str**|  | 
 **grant_type** | **str**|  | [optional] 
 **scope** | **str**|  | [optional] [default to &#39;&#39;]
 **client_id** | **str**|  | [optional] 
 **client_secret** | **str**|  | [optional] 

### Return type

[**Token**](Token.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/x-www-form-urlencoded
 - **Accept**: application/json

### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

