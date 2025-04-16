import logging

from textual import on
from textual.containers import Horizontal

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

	#vms {
	  height: 4fr;
	}
	"""

	def __init__(self, api: VBoxAPI, *args, **kwargs):
		self.api = api

		self.vms: list[models.Machine] = api.machines

		for vm in self.vms:
			logging.info(f"{self.api.performance_collector.setup_metrics(None, vm, 2, 1)}")
			logging.info(f"{self.api.performance_collector.enable_metrics(None, vm)}")

		super().__init__(*args, **kwargs)

	def query_metrics(self):
		vm_summary = {}
		for vm in self.vms:
			vm_pane: VM = self.query("#ID" + vm.id).first(VM)
			raw_metrics = self.api.performance_collector.query_metrics_data(None, vm)
			summary = {}
			for name, _, unit, scale, _, _, _, value in zip(*(raw_metrics[key] for key in raw_metrics)):

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
		with TabbedContent(id="vms"):
			for vm in self.vms:
				with TabPane(vm.name):
					yield VM(vm, self.api, id= "ID" + vm.id)

	@on(Button.Pressed, "#create-btn")
	def create_vm(self, event: Button.Pressed):
		self.app.push_screen(
			CreateModal(self.api),
			callback=lambda x: logging.warning("Create Done" + str(x))
		)

	def on_mount(self):
		self.title = "VBoxUI"
		self.set_interval(2, self.query_metrics)
