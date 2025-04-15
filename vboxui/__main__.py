from textual.app import App, ComposeResult
from vbox_api.helpers import start_vboxwebsrv

import logging

from .login import Login
from .vms import VMList

logging.basicConfig(filename='app.log', level=logging.INFO, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

API = None

class VboxApp(App):

    def on_mount(self) -> None:
        
        self.install_screen(Login(), name="login")

        def setup_screens(api):
            global API
            API = api
            self.install_screen(VMList(api), name="list")
            logging.info(api.machines)
            print(api.machines[0].name)
            self.push_screen("list")

        self.push_screen("login", setup_screens)


if __name__ == "__main__":
    start_vboxwebsrv()
    app = VboxApp()
    app.run()