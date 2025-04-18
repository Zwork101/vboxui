import time
from getpass import getpass, getuser
import logging

import requests.exceptions

from vbox_api import SOAPInterface, VBoxAPI


def build_api(
    username: str,
    password: str,
    host: str = "127.0.0.1",
    port: int = 18083,
    attempts: int = 5,
) -> VBoxAPI:
    interface = SOAPInterface(host, port)  # SOAP interface is used to interact with the VirtualBox API
    for _ in range(attempts):
        try:
            interface.connect()
            break
        except requests.exceptions.ConnectionError:
            time.sleep(2)
    else:
        print(f"Connection to {host}:{port} failed " f"after {attempts} attempts.")
        print("Check if vboxwebsrv is running on the host.")
        exit(1)

    logging.info("Connected")
    api = VBoxAPI(interface)  # pyright: ignore [reportArgumentType]
    if not api.login(username, password):
        print("Login failed.")
        exit(1)  # TODO: Add better login failure handling

    logging.info("returning API")
    return api  # pyright: ignore [reportReturnType]
