from getpass import getuser
import logging
import os
from pathlib import Path
import time

import psutil
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.validation import Integer, ValidationResult, Validator
from textual.widgets import Button, Header, Input, Label, Markdown, Static, Tab, TabPane, TabbedContent, Tabs
from textual_slider import Slider
from textual_fspicker import SelectDirectory, FileOpen
from vbox_api import VBoxAPI
from vbox_api.constants import AccessMode, MediumDeviceType, MediumState, MediumVariant
from vbox_api.models import Machine


class UniqueName(Validator):

    def __init__(self, api: VBoxAPI, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = api

    def validate(self, value: str) -> ValidationResult:
        found = next((m for m in self.api.machines if m.name == value), None)
        if not found:
            return self.success()
        else:
            return self.failure("Already existing machine shares that name", value)


class PathExists(Validator):

    def __init__(self, *args, target_directory: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_directory = target_directory

    def validate(self, value: str) -> ValidationResult:
        p = Path(value)
        if p.exists():
            if p.is_dir() and self.target_directory:
                return self.success()
            elif not p.is_dir() and self.target_directory:
                return self.failure("Path must be a directory")
            elif p.is_file() and not self.target_directory:
                return self.success()
            else:
                return self.failure("Path must be a file")
        else:
            return self.failure("Path does not exist")


class CreateModal(ModalScreen[Machine]):
    DEFAULT_CSS = """
    CreateModal {
        align: center middle;
    }

    CreateModal > Container {
        width: 80%;
        height: 90%;
        border: thick $background 80%;
        background: $surface;
    }

    .form-option > Horizontal {
        content-align: left middle;
    }

    .form-option > Horizontal > Static {
        width: 1fr;
    }

    .form-option > Horizontal > Input {
        width: 3fr;
    }

    .form-option > Horizontal > .surround {
        width: 3fr;
        content-align: center middle;
    }

    .surround > Static {
        width: 1fr;
    }

    .surround > Slider {
        width: 5fr;
    }

    .surround > Input {
        width: 4fr;
    }

    .surround > Button {
        width: 2fr;
    }

    .error-message {
        display: none;
    }

    #header {
        height: 1fr;
    }

    TabbedContent {
        height: 5fr;
        border: round blue;
    }

    TabPane {
        border: round red;
    }

    #options {
        height: 1fr;
        content-align: right middle;
    }
    """

    tab_form = [
        ("tab-init", ["name-input", "parent-input", "iso-input"]),
        ("tab-hardware", ["memory-input", "cpu-input"]),
        ("tab-storage", ["slocation-input", "ssize-input"])
    ]

    def __init__(self, api: VBoxAPI, *args, **kwargs):
        super().__init__(*args, **kwargs)

        mem = psutil.virtual_memory()
        self._max_cpu_cores = psutil.cpu_count() or 2
        self._max_memory = mem.total // 1_000_000
        self._api = api
        self.form_data = {
            "name-input": "",
            "parent-input": f"/home/{getuser()}/VirtualBox VMs",
            "iso-input": "",
            "memory-input": max(self._max_memory // 4, 500),
            "cpu-input": 1,
            "slocation-input": f"/home/{getuser()}/VirtualBox VMs",
            "ssize-input": "4"
        }
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Create a new Machine", id="header")
            with TabbedContent():
                with TabPane("Init", id="tab-init"):
                    with Vertical(classes="form-option"):
                        with Horizontal():
                            yield Static("Machine Name")
                            yield Input(self.form_data['name-input'], id="name-input", validators=[UniqueName(self._api)], validate_on=["changed"], placeholder="Unique Machine Name")
                        yield Static(f"", classes="error-message", id="error-name")
                    with Vertical(classes="form-option"):
                        with Horizontal():
                            yield Static("VM Directory")
                            with Horizontal(classes="surround"):
                                yield Input(self.form_data['parent-input'], id="parent-input", validators=[PathExists(target_directory=True)], validate_on=["changed"])
                                yield Button("Select Directory", id="parent-btn", classes="filepicker")
                        yield Static(f"", classes="error-message", id="error-parent")
                    with Vertical(classes="form-option"):
                        with Horizontal():
                            yield Static("VM ISO Image")
                            with Horizontal(classes="surround"):
                                yield Input(self.form_data['iso-input'], id="iso-input", validators=[PathExists(target_directory=False)], validate_on=["changed"])
                                yield Button("Select File", id="iso-btn", classes="filepicker")
                        yield Static(f"", classes="error-message", id="error-iso")
                with TabPane("Hardware", disabled=True, id="tab-hardware"):
                    with Vertical(classes="form-option"):
                        with Horizontal():
                            yield Static(f"Base Memory: {self.form_data['memory-input']} MB", id="memory-target")
                            with Horizontal(classes="surround"):
                                yield Static("500")
                                yield Slider(min=500, max=self._max_memory, step=100, id="memory-input", value=self.form_data["memory-input"])
                                yield Static(str(self._max_memory))
                        yield Static(f"", classes="error-message", id="error-memory")
                    with Vertical(classes="form-option"):
                        with Horizontal():
                            yield Static(f"CPU Cores: {self.form_data['cpu-input']}", id="cpu-target")
                            with Horizontal(classes="surround"):
                                yield Static("1")
                                yield Slider(min=1, max=self._max_cpu_cores, step=1, id="cpu-input", value=self.form_data["cpu-input"])
                                yield Static(str(self._max_cpu_cores))
                        yield Static(f"", classes="error-message", id="error-memory")
                with TabPane("Storage", disabled=True, id="tab-storage"):
                    with Vertical(classes="form-option"):
                        with Horizontal():
                            yield Static("Storage Location")
                            with Horizontal(classes="surround"):
                                yield Input(self.form_data['slocation-input'], id="slocation-input", validators=[PathExists(target_directory=True)], validate_on=["changed"])
                                yield Button("Select Directory", id="slocation-btn", classes="filepicker")
                        yield Static(f"", classes="error-message", id="error-slocation")
                    with Vertical(classes="form-option"):
                        with Horizontal():
                            yield Static("Storage Size (MB)")
                            yield Input(self.form_data['ssize-input'], id="ssize-input", type="integer", validators=[Integer(4, psutil.disk_usage("/").free // 1_000_000)], validate_on=["changed"])
                        yield Static(f"", classes="error-message", id="error-ssize")
            with Horizontal(id="options"):
                yield Button("Continue", variant="primary", id="continue-btn", disabled=True)
                yield Button("Cancel", variant="error", id="cancel-btn")

    def on_mount(self):
        # self.query_one(TabbedContent).select()
        self.query_exactly_one("#name-input", Input).focus()
        

    @on(Button.Pressed, ".filepicker")
    @work
    async def select_directory(self, event: Button.Pressed):
        attribute = event.button.id
        if attribute is None:
            logging.warning("File picker lacks ID")
            return
        attribute = attribute.split("-")[0]
        if str(event.button.label).startswith("Directory"):
            opened = await self.app.push_screen_wait(SelectDirectory(self.form_data[f"{attribute}-input"]))
        else:
            opened = await self.app.push_screen_wait(FileOpen(self.form_data[f"{attribute}-input"]))
        if opened:
            self.query_exactly_one(f"#{attribute}-input", Input).value = str(opened)

    @on(Slider.Changed)
    def update_slider(self, event: Slider.Changed):
        slider_id = event.slider.id
        if not slider_id:
            logging.warning("Slider is missing ID")
            return

        slider_name = slider_id.split("-")[0]
        if slider_name == "memory":
            self.query_exactly_one("#" + slider_name + "-target", Static).update(f"Base Memory: {event.value} MB")
        elif slider_name == "cpu":
            self.query_exactly_one("#" + slider_name + "-target", Static).update(f"CPU Cores: {event.value}")

    @on(Button.Pressed, "#continue-btn")
    def continue_step(self):
        tabbed_content = self.query_exactly_one(TabbedContent).active_pane
        if not tabbed_content or not tabbed_content.id:
            logging.warning("Continue hit without tab pane selected")
            return
        
        tab_name = tabbed_content.id
        tab_inputs = next((t[1] for t in self.tab_form if t[0] == tab_name), None)

        if tab_inputs is None:
            logging.warning(f"Unable to find tab inputs for {tab_name}")
            return

        next_tab = self.tab_form.index((tab_name, tab_inputs)) + 1

        if next_tab == len(self.tab_form):
            return self.create_machine()

        self.query_exactly_one(TabbedContent).active = self.tab_form[next_tab][0]
        self.check_active_tab(self.query_exactly_one(TabbedContent).active_pane)  # pyright: ignore [reportArgumentType]

    @on(Button.Pressed, "#cancel-btn")
    def stop_setup(self, event: Button.Pressed):
        self.app.pop_screen()  # TODO: RAHIUHBIUHDWUJABDUJAHWBUJHABUHJACVBUIJWCVBAUJIWCHBBJAWC WHY DID I DO THAT

    @on(Input.Changed)
    @work
    async def display_errors(self, event: Input.Changed):
        if event.input.id is None:
            logging.warning("Input element lacks ID")
            return
        
        if event.validation_result is not None:
            err_element = self.query_exactly_one("#error-" + event.input.id.split("-")[0], Static)
            if not event.validation_result.is_valid:
                err_element.update("*" + ", ".join(event.validation_result.failure_descriptions) + "*")
                err_element.styles.display = "block"
            else:
                self.form_data[event.input.id] = event.value
                err_element.styles.display = "none"

        active_tab = self.query_exactly_one(TabbedContent).active_pane

        if not active_tab or not active_tab.id:
            logging.warning("Active tab not found or has no ID")
            return

        self.check_active_tab(active_tab, event)

    def check_active_tab(self, active_tab: TabPane | Tab, event: Input.Changed | None = None):
        if active_tab.id is None:
            return
        
        tab_name = active_tab.id
        tab_inputs = next((t[1] for t in self.tab_form if t[0] == tab_name), None)

        if tab_inputs is None:
            logging.warning(f"Unable to find tab inputs for {tab_name}")
            return

        next_tab = self.tab_form.index((tab_name, tab_inputs)) + 1

        if all(self.form_data[inp] for inp in tab_inputs):
            if next_tab != len(self.tab_form):
                self.query_exactly_one("#" + self.tab_form[next_tab][0], TabPane).disabled = False

            if event and event.input.id in tab_inputs:
                logging.info(self.form_data, tab_inputs)
                self.query_exactly_one("#continue-btn", Button).disabled = False
        else:
            if next_tab != len(self.tab_form):
                self.query_exactly_one("#" + self.tab_form[next_tab][0], TabPane).disabled = True

            if event and event.input.id in tab_inputs:
                self.query_exactly_one("#continue-btn", Button).disabled = True

    def create_machine(self):
        unattended = self._api.ctx.api.create_unattended_installer()
        unattended.iso_path = self.form_data['iso-input']
        logging.info(unattended.iso_path)
        # unattended.detect_iso_os()
        settings_path = self._api.compose_machine_filename(self.form_data['name-input'], "/", "", self.form_data['parent-input'])
        architecture = self._api.host.architecture
        machine: Machine = self._api.create_machine(
            settings_path, self.form_data['name-input'], architecture, ["/"], 'Linux26_64', "", "", "", ""  # Try and use detect OS type
        )
        machine.apply_defaults("")
        self._api.register_machine(machine)

        with machine.with_lock(save_settings=True, force_unlock=True) as mut_machine:
            mut_machine.cpu_count = self.form_data['cpu-input']
            mut_machine.memory_size = self.form_data['memory-input']
            medium = self._api.create_medium(
                "", 
                os.path.join(self.form_data['slocation-input'], self.form_data['name-input'] + '.vdi'), 
                AccessMode.READ_WRITE, 
                MediumDeviceType.HARD_DISK
            )
            logging.info(self.form_data['ssize-input'])
            progress = medium.create_base_storage(((int(self.form_data['ssize-input']) * 1_000_000) // 512) * 512, ["Standard"])
        
            progress.wait_for_completion(10)
            medium.refresh_state()
            logging.info(medium.state)

            iso_medium = self._api.open_medium(
                self.form_data['iso-input'],
                "DVD",
                AccessMode.READ_ONLY,
                True
            )

            mut_machine.attach_medium(
                iso_medium,
                "IDE"
            )

            mut_machine.attach_medium(
                medium,
                "SATA"
            )
        
        self.dismiss(machine)
    
