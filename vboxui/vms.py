import logging

from textual import on, work
from textual.containers import Horizontal
from textual.css.query import NoMatches

from vboxui.create import CreateModal
from .models import Metric

from textual.screen import Screen
from textual.widgets import Button, Header, TabbedContent, TabPane
from vbox_api import VBoxAPI, models

from vboxui.instance import VM


class VMList(Screen):
    DEFAULT_CSS = """
	Screen {
	  layout: vertical;
	}

	#options {
	  height: 1fr;
	}

	#options > * {
	  margin: 1 1 0 1
	}

	#vms {
	  height: 4fr;
	}
	"""

    def __init__(self, api: VBoxAPI, *args, **kwargs):
        self.api = api

        self.vms: list[models.Machine] = api.machines

        for vm in self.vms:
            logging.info(
                f"{self.api.performance_collector.setup_metrics(None, vm, 2, 1)}"
            )
            logging.info(f"{self.api.performance_collector.enable_metrics(None, vm)}")  # Enable metrics for all VMs

        super().__init__(*args, **kwargs)

    def query_metrics(self):
        vm_summary = {}
        for vm in self.vms:
            try:
                vm_pane: VM = self.query("#ID" + vm.id).first(VM)
            except NoMatches:
                continue
            raw_metrics = self.api.performance_collector.query_metrics_data(None, vm)
            summary = {}
            for name, _, unit, scale, _, _, _, value in zip(
                *(raw_metrics[key] for key in raw_metrics)
            ):
                # Setting these values will also automatically update the display

                if name == "CPU/Load/User":
                    vm_pane.metric_cpu_user_load = Metric(value, scale, unit)
                elif name == "CPU/Load/Kernel":
                    vm_pane.metric_cpu_kernel_load = Metric(value, scale, unit)
                elif name == "CPU/Usage/Used":
                    vm_pane.metric_mem_usage = Metric(value, scale, unit)
                elif name == "Disk/Usage/Used":
                    vm_pane.metric_disk_used = Metric(value, scale, unit)
                elif name == "Net/Rate/Rx":
                    vm_pane.metric_network_rx = Metric(value, scale, unit)
                elif name == "Net/Rate/Tx":
                    vm_pane.metric_network_tx = Metric(value, scale, unit)

                summary[name] = value, scale, unit
            vm_summary[vm] = summary
        return vm_summary

    def compose(self):
        yield Header()
        with Horizontal(id="options"):
            yield Button("Create VM", variant="success", id="create-btn")
            yield Button(
                "Manage Mediums", variant="warning", id="manage-medium", disabled=True
            )
            yield Button(
                "Manage Networks", variant="warning", id="manage-net", disabled=True
            )
            yield Button(
                "Manage Logs", variant="warning", id="manage-logs", disabled=True
            )
            yield Button("Exit VboxUI", variant="error", id="leave-btn")

        with TabbedContent(id="vms"):
            for vm in self.vms:
                with TabPane(vm.name):
                    yield VM(vm, self.api, id="ID" + vm.id)

    @on(Button.Pressed, "#leave-btn")
    def exit_app(self):
        self.app.exit()

    @on(Button.Pressed, "#create-btn")
    @work()
    async def create_vm(self, event: Button.Pressed):
        m = await self.app.push_screen_wait(CreateModal(self.api))
        self.vms.append(m)
        await self.recompose()

    def on_mount(self):
        self.title = "VM List"
        self.set_interval(2, self.query_metrics)
