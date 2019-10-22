# -*- coding: utf-8 -*-

# Copyright 2019 Univention GmbH
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

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any, Coroutine, Dict, List, Union

import lazy_object_proxy
import ujson
import zmq
import zmq.asyncio
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import HTMLResponse, UJSONResponse
from starlette.staticfiles import StaticFiles
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from . import __version__
from .constants import (
    HISTORY_FILE,
    LOG_FILE_PATH_HTTP,
    README_FILE,
    RPC_ADDR,
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
from .utils import ConsoleAndFileLogging, get_token_ttl

router = APIRouter()
zmq_context = zmq.asyncio.Context()
ConsoleAndFileLogging.get_logger("uvicorn", LOG_FILE_PATH_HTTP)
logger = ConsoleAndFileLogging.get_logger(__name__, LOG_FILE_PATH_HTTP)
ldap_auth_instance: LDAPAccess = lazy_object_proxy.Proxy(LDAPAccess)


@router.get("/school_to_authority_mapping", tags=["school_to_authority_mapping"])
async def read_school_to_school_authority_mapping(
    current_user: User = Depends(get_current_active_user)
) -> School2SchoolAuthorityMapping:
    res = await query_service(cmd="get_school_to_authority_mapping")
    if res.get("errors"):
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=res["errors"]
        )
    return School2SchoolAuthorityMapping(**res["result"])


@router.put("/school_to_authority_mapping", tags=["school_to_authority_mapping"])
async def put_school_to_school_authority_mapping(
    school_to_authority_mapping: School2SchoolAuthorityMapping,
    current_user: User = Depends(get_current_active_user),
) -> School2SchoolAuthorityMapping:
    logger.info(
        "User %r modifying school to school authority mapping...", current_user.username
    )
    res = await query_service(
        cmd="put_school_to_authority_mapping",
        school_to_authority_mapping=school_to_authority_mapping,
    )
    if res.get("errors"):
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=res["errors"]
        )
    return School2SchoolAuthorityMapping(**res["result"])


@router.get("/queues", response_model=List[QueueModel], tags=["queues"])
async def read_queues(
    current_user: User = Depends(get_current_active_user)
) -> List[QueueModel]:
    res = await query_service(cmd="get_queues")
    resp = AllQueues(**res["result"])
    return [resp.in_queue] + resp.out_queues


@router.get("/queues/{name}", response_model=QueueModel, tags=["queues"])
async def read_queue(
    name: str, current_user: User = Depends(get_current_active_user)
) -> QueueModel:
    res = await query_service(cmd="get_queue", name=name)
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=res["errors"])
    return QueueModel(**res["result"])


@router.get("/school_authorities", tags=["school_authorities"])
async def read_school_authorities(
    current_user: User = Depends(get_current_active_user)
) -> List[SchoolAuthorityConfiguration]:
    res = await query_service(cmd="get_school_authorities")
    return sorted(
        [SchoolAuthorityConfiguration(**r) for r in res["result"]], key=lambda x: x.name
    )


@router.post(
    "/school_authorities", tags=["school_authorities"], status_code=HTTP_201_CREATED
)
async def create_school_authorities(
    school_authority: SchoolAuthorityConfiguration,
    current_user: User = Depends(get_current_active_user),
) -> SchoolAuthorityConfiguration:
    logger.info(
        "User %r creating school authority %r...",
        current_user.username,
        school_authority,
    )
    res = await query_service(
        cmd="create_school_authority", school_authority=school_authority
    )
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=res["errors"])
    return SchoolAuthorityConfiguration(**res["result"])


@router.get("/school_authorities/{name}", tags=["school_authorities"])
async def read_school_authority(
    name: str, current_user: User = Depends(get_current_active_user)
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
    name: str, current_user: User = Depends(get_current_active_user)
) -> None:
    logger.info("User %r deleting school authority %r...", current_user.username, name)
    res = await query_service(cmd="delete_school_authority", name=name)
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=res["errors"])
    return None


@router.patch(
    "/school_authorities/{name}", tags=["school_authorities"], status_code=HTTP_200_OK
)
async def patch_school_authority(
    name: str,
    school_authority: SchoolAuthorityConfigurationPatchDocument,
    current_user: User = Depends(get_current_active_user),
) -> SchoolAuthorityConfiguration:
    # We could use status_code=204 for PATCH, but then we must not return anything.
    # IMHO that is less useful than using 200 and returning the modified resource.
    logger.info("User %r modifying school authority %r...", current_user.username, name)
    res = await query_service(
        cmd="patch_school_authority", name=name, school_authority=school_authority
    )
    if res.get("errors"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=res["errors"])
    return SchoolAuthorityConfiguration(**res["result"])


# TODO: resources ProfS needs for setup/testing:
# TODO: sync_user(uid)
# TODO: sync_school_class(ou, class_name)
# TODO: sync_school(ou)
# TODO: sync_school_authority(s_a_c)


@asyncio.coroutine
def query_service(
    cmd: str,
    name: str = None,
    school_authority: Union[
        SchoolAuthorityConfiguration, SchoolAuthorityConfigurationPatchDocument
    ] = None,
    school_to_authority_mapping: School2SchoolAuthorityMapping = None,
) -> Coroutine[Dict[str, Any], None, None]:
    request_kwargs = {"cmd": RPCCommand(cmd)}
    if name is not None:
        request_kwargs["name"] = name
    if school_authority is not None:
        request_kwargs["school_authority"] = school_authority.dict()
        if school_authority.password:
            request_kwargs["school_authority"][
                "password"
            ] = school_authority.password.get_secret_value()
    if school_to_authority_mapping is not None:
        request_kwargs[
            "school_to_authority_mapping"
        ] = school_to_authority_mapping.dict()
    request = RPCRequest(**request_kwargs)
    # logger.debug("Querying queue daemon: %r", request.dict())
    socket = zmq_context.socket(zmq.REQ)
    socket.connect(RPC_ADDR)
    yield from socket.send_string(request.json())
    response = yield from socket.recv_string()
    # logger.debug("Received response: %r", response)
    return ujson.loads(response)


app = FastAPI(
    title="ID Sync API",
    description="API to monitor queues and manage the configuration.",
    version=__version__,
    docs_url=f"{URL_PREFIX}/docs",
    redoc_url=f"{URL_PREFIX}/redoc",
    openapi_url=f"{URL_PREFIX}/openapi.json",
    default_response_class=UJSONResponse,
)


@app.post(TOKEN_URL, response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await ldap_auth_instance.check_auth_and_get_user(
        form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=await get_token_ttl())
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
app.mount(
    f"{URL_PREFIX}/static",
    StaticFiles(directory=str(Path(__file__).parent.parent / "static")),
    name="static",
)
