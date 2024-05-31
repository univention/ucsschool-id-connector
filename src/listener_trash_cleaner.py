#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta

from ucsschool_id_connector.utils import get_ucrv

TRASH_PATH = "/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/listener/trash/"


def delete_up_from_day(offset: int = 0, trash_path: str = TRASH_PATH) -> None:
    delete_time = datetime.now() - timedelta(days=offset)
    for filename in os.listdir(trash_path):
        f = os.path.join(trash_path, filename)
        file_time = datetime.fromtimestamp(os.stat(f).st_mtime)
        if file_time < delete_time and os.path.isfile(f):
            os.remove(f)


def run() -> None:
    if int(get_ucrv("ucsschool-id-connector/trash_delete_state", 1)) == 1:
        delete_up_from_day(offset=int(get_ucrv("ucsschool-id-connector/trash_delete_offset", 30)))


if __name__ == "__main__":
    run()
