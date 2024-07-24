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

import logging
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Union

import lazy_object_proxy
import ujson
import zmq
import zmq.asyncio
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse, RedirectResponse, Response, UJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from .constants import (
    APP_ID,
    HISTORY_FILE,
    LOG_FILE_PATH_HTTP,
    README_FILE,
    RPC_ADDR,
    RPC_CLIENT_TIMEOUT,
    TOKEN_URL,
    URL_PREFIX,
)
from .ldap_access import LDAPAccess
from .models import (
    AllQueues,
    QueueModel,
    RPCCommand,
    RPCRequest,
    School2SchoolAuthorityMapping,
    SchoolAuthorityConfiguration,
    SchoolAuthorityConfigurationPatchDocument,
    Token,
    User,
)
from .token_auth import create_access_token, get_current_active_user
from .utils import ConsoleAndFileLogging, get_app_version, get_token_ttl

router = APIRouter()
zmq_context = zmq.asyncio.Context()
ldap_auth_instance: LDAPAccess = lazy_object_proxy.Proxy(LDAPAccess)


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    ConsoleAndFileLogging.get_logger("uvicorn", LOG_FILE_PATH_HTTP)
    return ConsoleAndFileLogging.get_logger(__name__, LOG_FILE_PATH_HTTP)


@router.get("/school_to_authority_mapping", tags=["school_to_authority_mapping"])
async def read_school_to_school_authority_mapping(
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> School2SchoolAuthorityMapping:
    res = await query_service(cmd="get_school_to_authority_mapping")
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=res["errors"])
    return School2SchoolAuthorityMapping(**res["result"])


@router.put("/school_to_authority_mapping", tags=["school_to_authority_mapping"])
async def put_school_to_school_authority_mapping(
    school_to_authority_mapping: School2SchoolAuthorityMapping,
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> School2SchoolAuthorityMapping:
    logger.info("User %r modifying school to school authority mapping...", current_user.username)
    res = await query_service(
        cmd="put_school_to_authority_mapping",
        school_to_authority_mapping=school_to_authority_mapping,
    )
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=res["errors"])
    return School2SchoolAuthorityMapping(**res["result"])


@router.get("/queues", response_model=List[QueueModel], tags=["queues"])
async def read_queues(
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> List[QueueModel]:
    res = await query_service(cmd="get_queues")
    resp = AllQueues(**res["result"])
    return [resp.in_queue] + resp.out_queues


@router.get("/queues/{name}", response_model=QueueModel, tags=["queues"])
async def read_queue(
    name: str,
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> QueueModel:
    res = await query_service(cmd="get_queue", name=name)
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=res["errors"])
    return QueueModel(**res["result"])


@router.get("/school_authorities", tags=["school_authorities"])
async def read_school_authorities(
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> List[SchoolAuthorityConfiguration]:
    res = await query_service(cmd="get_school_authorities")
    return sorted([SchoolAuthorityConfiguration(**r) for r in res["result"]], key=lambda x: x.name)


@router.post("/school_authorities", tags=["school_authorities"], status_code=HTTP_201_CREATED)
async def create_school_authorities(
    school_authority: SchoolAuthorityConfiguration,
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> SchoolAuthorityConfiguration:
    logger.info(
        "User %r creating school authority %r...",
        current_user.username,
        school_authority,
    )
    res = await query_service(cmd="create_school_authority", school_authority=school_authority)
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=res["errors"])
    return SchoolAuthorityConfiguration(**res["result"])


@router.get("/school_authorities/{name}", tags=["school_authorities"])
async def read_school_authority(
    name: str,
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> SchoolAuthorityConfiguration:
    res = await query_service(cmd="get_school_authority", name=name)
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=res["errors"])
    return SchoolAuthorityConfiguration(**res["result"])


@router.delete(
    "/school_authorities/{name}",
    tags=["school_authorities"],
    status_code=HTTP_204_NO_CONTENT,
)
async def delete_school_authority(
    name: str,
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> Response:
    logger.info("User %r deleting school authority %r...", current_user.username, name)
    res = await query_service(cmd="delete_school_authority", name=name)
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=res["errors"])
    return Response(status_code=HTTP_204_NO_CONTENT)


@router.patch("/school_authorities/{name}", tags=["school_authorities"], status_code=HTTP_200_OK)
async def patch_school_authority(
    name: str,
    school_authority: SchoolAuthorityConfigurationPatchDocument,
    current_user: User = Depends(get_current_active_user),
    logger: logging.Logger = Depends(get_logger),
) -> SchoolAuthorityConfiguration:
    # We could use status_code=204 for PATCH, but then we must not return anything.
    # IMHO that is less useful than using 200 and returning the modified resource.
    logger.info("User %r modifying school authority %r...", current_user.username, name)
    res = await query_service(cmd="patch_school_authority", name=name, school_authority=school_authority)
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=res["errors"])
    return SchoolAuthorityConfiguration(**res["result"])


async def query_service(
    cmd: str,
    name: str = None,
    school_authority: Union[
        SchoolAuthorityConfiguration, SchoolAuthorityConfigurationPatchDocument
    ] = None,
    school_to_authority_mapping: School2SchoolAuthorityMapping = None,
) -> Dict[str, Any]:
    request_kwargs = {"cmd": RPCCommand(cmd)}
    if name is not None:
        request_kwargs["name"] = name
    if school_authority is not None:
        request_kwargs["school_authority"] = school_authority.dict_secrets_as_str()
    if school_to_authority_mapping is not None:
        request_kwargs["school_to_authority_mapping"] = school_to_authority_mapping.dict()
    request = RPCRequest(**request_kwargs)
    # logger.debug("Querying queue daemon: %r", request.dict())
    socket = zmq_context.socket(zmq.REQ)
    socket.RCVTIMEO = RPC_CLIENT_TIMEOUT
    socket.connect(RPC_ADDR)
    await socket.send_string(request.json())
    try:
        response = await socket.recv_string()
    except zmq.error.ZMQError as exc:
        get_logger().fatal("Error waiting for response from RPC server: %s", exc)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No/Bad response from connector.",
        )
    # logger.debug("Received response: %r", response)
    return ujson.loads(response)


app = FastAPI(
    title="UCS@school ID Connector API",
    description="API to monitor queues and manage the configuration.",
    docs_url=None,
    redoc_url=None,
    version=get_app_version(),
    openapi_url=f"{URL_PREFIX}/openapi.json",
    default_response_class=UJSONResponse,
)

app.mount(
    f"{URL_PREFIX}/static", StaticFiles(directory=(Path(__file__).parent / "static")), name="static"
)


@app.get(f"{URL_PREFIX}/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url=f"{URL_PREFIX}/static/swagger-ui-bundle-5.17.14.min.js",
        swagger_css_url=f"{URL_PREFIX}/static/swagger-ui-5.17.14.min.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get(f"{URL_PREFIX}/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url=f"{URL_PREFIX}/static/redoc.standalone-2.0.0-rc.75.js",
    )


@app.get(f"/{APP_ID}/api/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url=f"{URL_PREFIX}/docs")


@app.post(TOKEN_URL, response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    logger: logging.Logger = Depends(get_logger),
):
    user = await ldap_auth_instance.check_auth_and_get_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=get_token_ttl())
    access_token = await create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    logger.debug("User %r retrieved access_token.", user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get(f"{URL_PREFIX}/history", response_class=HTMLResponse)
def get_history():
    with open(Path(__file__).parent.parent / HISTORY_FILE) as fp:
        return fp.read()


@app.get(f"{URL_PREFIX}/readme", response_class=HTMLResponse)
def get_readme():
    with open(Path(__file__).parent.parent / README_FILE) as fp:
        return fp.read()


app.include_router(router, prefix=URL_PREFIX)
