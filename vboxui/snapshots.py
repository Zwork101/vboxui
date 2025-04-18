from datetime import datetime
import time

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Markdown, Static, Switch, TextArea
from vbox_api.models import Machine
from vbox_api.models.machine import MachineHealth
from zeep.exceptions import Fault


class TakeSnapshot(ModalScreen):
    DEFAULT_CSS = """
    TakeSnapshot {
        align: center middle;
    }

    TakeSnapshot > Vertical {
        width: 50%;
        height: 90%;
        border: thick $background 80%;
        background: $surface;
        padding: 3;
    }

    Horizontal {
        height: 1fr;
        width: 100%;
    }

    Horizontal > Static {
        width: 1fr;
    }

    Horizontal > TextArea {
        width: 3fr;
    }

    Horizontal > Input {
        width: 3fr;
    }

    #btns {
        content-align: left middle;
    }

    #btns > Button {
        margin: 0 2 0 0;
    }
    """

    def __init__(self, machine: Machine, *args, **kwargs):
        self._vbox = machine
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Markdown("**Create a Snapshot**")
            with Horizontal():
                yield Static("Snapshot Name")
                yield Input(id="snap-name")
            with Horizontal():
                yield Static("Snapshot Description")
                yield TextArea(id="snap-desc")
            with Horizontal():
                yield Static("Pause for Snapshot")
                yield Switch(
                    id="snap-pause",
                    disabled=self._vbox.health != MachineHealth.RUNNING,
                    value=False,
                )
            with Horizontal(id="btns"):
                yield Button(
                    "Take Snapshot", id="take-btn", disabled=True, variant="success"
                )
                yield Button("Cancel Snapshot", id="cancel-btn", variant="error")

    @on(Input.Changed, "#snap-name")
    def check_name(self, event: Input.Changed):
        # Only allow submit if a snapshot name is provided
        if event.value:
            self.query_exactly_one("#take-btn", Button).disabled = False
        else:
            self.query_exactly_one("#take-btn", Button).disabled = True

    @on(Button.Pressed, "#take-btn")
    def create_snap(self, event: Button.Pressed):
        with self._vbox.with_lock() as mut_machine:
            mut_machine.take_snapshot(
                self.query_exactly_one("#snap-name", Input).value,
                self.query_exactly_one("#snap-desc", TextArea).text,
                not self.query_exactly_one("#snap-pause", Switch).value,
            )
            for _ in range(20):
                if mut_machine.health != MachineHealth.WARNING:
                    break  # Must wait until MachineHealth is not WARNING before unlocking the VM. Learned this the hard way.
                time.sleep(0.5)
            else:
                raise TimeoutError("Unable to take snapshot")
        self.dismiss()

    @on(Button.Pressed, "#cancel-btn")
    def cancel_btn(self, event: Button.Pressed):
        self.dismiss()


class ListSnapshots(ModalScreen):
    DEFAULT_CSS = """
    ListSnapshots {
        align: center middle;
    }

    ListSnapshots > Vertical {
        width: 80%;
        height: 75%;
        border: thick $background 80%;
        background: $surface;
        padding: 3;
    }

    DataTable {
        height: 40%;
    }

    Vertical > * {
        margin: 2 1
    }

    Horizontal > Input {
        width: 2fr;
    }

    Horizontal > Button {
        width: 1fr;
    }
    """

    def __init__(self, machine: Machine, *args, **kwargs):
        self._vbox = machine
        self._selected_snapshot = None
        self.snapshots = {}
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select a snapshot to revert to")
            yield DataTable(
                fixed_columns=6, cursor_type="row", zebra_stripes=True, id="snapshots"
            )  # TODO: Will add better selection system later, but this is solid right now
            with Horizontal():
                yield Input(disabled=True, id="selected-snapshot")
                yield Button(
                    "Perform Revert", id="revert-btn", variant="success", disabled=True
                )
                yield Button("Cancel Revert", id="cancel-btn", variant="error")

    @on(Button.Pressed, "#cancel-btn")
    def end_revert(self, event: Button.Pressed):
        self.dismiss()

    @on(Button.Pressed, "#revert-btn")
    def return_snapshot(self, event: Button.Pressed):
        self.dismiss(self.snapshots[self._selected_snapshot])

    @on(DataTable.RowSelected, "#snapshots")
    def select_snapshot(self, event: DataTable.RowSelected):
        snap_display = self.query_exactly_one("#selected-snapshot", Input)
        snap_display.value = event.data_table.get_row_at(event.cursor_row)[0]
        self.query_exactly_one("#revert-btn", Button).disabled = False
        self._selected_snapshot = snap_display.value

    @classmethod
    def flatten_snapshots(cls, snapshot) -> list:
        current_list = []
        current_list.append(snapshot)
        for child in snapshot.children:
            current_list += cls.flatten_snapshots(child)
        return current_list

    def on_mount(self):
        snapshot_table = self.query_exactly_one("#snapshots", DataTable)
        snapshot_table.add_columns(
            "id", "name", "description", "online", "parent", "timestamp"
        )
        try:
            snapshots = self.flatten_snapshots(self._vbox.find_snapshot(""))
        except Fault:
            return

        for snapshot in snapshots:
            self.snapshots[snapshot.id] = snapshot
            timestamp = datetime.fromtimestamp(snapshot.time_stamp / 1000).strftime(
                "%m/%-d/%Y %H:%M"
            )
            snapshot_table.add_row(
                snapshot.id,
                snapshot.name,
                snapshot.description,
                "Online" if snapshot.online else "Offline",
                "-" if not snapshot.parent else snapshot.parent.name,
                timestamp,
            )
