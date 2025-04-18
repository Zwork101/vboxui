from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Container
from textual.logging import TextualHandler
from textual.widgets import Header, Input, Label, Static, Button

from .api import build_api

from getpass import getuser
import logging


class Login(Screen):
    CSS = """
    #Main { 
    align: center middle; 
    layout: grid;
    grid-size: 5 8;
    }

    Horizontal {
    content-align: center middle;
    layout: grid;
    grid-size: 3;
    margin-top: 2;
    }

    #button-menu {
    grid-size: 7;
    }

    .login {
    border: solid blue;
    column-span: 2;
    row-span: 7;
    }

    .form-label {
    content-align: center middle;
    text-style: bold;
    height: 75%;
    }

    Button {
    column-span: 2;
    }

    .form-input {
    column-span: 2;
    }

    .err {
    visibility: hidden;
    content-align: center middle;
    text-style: bold;
    color: red;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="Main"):
            with Vertical(classes="login"):
                with Horizontal():
                    yield Static("Username", classes="form-label", id="username-text")
                    yield Input(
                        placeholder=getuser(), classes="form-input", id="username"
                    )
                with Horizontal():
                    yield Static("Password", classes="form-label", id="password-text")
                    yield Input(password=True, classes="form-input", id="password")
                with Horizontal(id="button-menu"):
                    yield Static()
                    yield Button("Login", variant="primary", id="login")
                    yield Static()
                    yield Button("Quit", variant="error", id="quit")
                    yield Static()
                yield Static("", classes="err")

    def on_mount(self):
        self.title = "VirtualBox Login"
        self.sub_title = f"Default User - {getuser()}"
        self.query_exactly_one("#password").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login":
            username = self.query_one("#username", Input).value or getuser()
            password = self.query_one("#password", Input)

            if not password.value:
                password.focus()
                password_text = self.query_one("#password-text")
                password_text.styles.color = "red"
                logging.info(username)
                logging.info(repr(self.query_one("#username-text").styles))

                err = self.query_one(".err", Static)
                err.styles.visibility = "visible"
                err.update("Error: Please enter a password")

            else:
                logging.info("Dismissing")
                self.dismiss(build_api(username, password.value))  # We don't check if password is wrong yet

        elif event.button.id == "quit":
            logging.warning("Quitting...")
            exit(0)
