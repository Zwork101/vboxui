import logging

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Static
from vbox_api.api import VBoxAPI
from vbox_api.models.machine import MachineHealth, Machine

class VM(Widget):
	"""
	.menu {
	  dock: left;
	  width: 20%;
	  height: 100%;
	}

	.information {
	  width: 80%;
	  height: 100%;
	}
	"""

	def __init__(self, machine: Machine, api: VBoxAPI):
		self._vbox = machine
		self._api = api
		self.vbox_name: str = machine.name
		self.vbox_os: str = machine.os_type_id
		self.vbox_cpu_count = machine.cpu_count
		self.vbox_memory = machine.memory_size
		self.vbox_health = machine.health
		self.vbox_networks = machine.network_adapters
		self.vbox_drives = []

		for attachment in machine.mediums:
			if attachment.type == 'HardDisk':
				self.vbox_drives.append(attachment)

		if self.vbox_health == MachineHealth.RUNNING:
			self.update_metrics()

		super().__init__()

	def compose(self) -> ComposeResult:
		with Horizontal(classes="instance"):
			with Vertical(classes="menu"):
				yield Button("Start VM", variant="success", disabled=self.vbox_health == MachineHealth.POWERED_OFF)
				yield Button("Stop VM", variant="primary", disabled=self.vbox_health == MachineHealth.RUNNING)
				yield Button("VM Settings", variant="warning")
				yield Button("Take Snapshot", variant="warning")
				yield Button("Delete VM", variant="error")
			with Container(classes="information"):
				yield Static(self.vbox_name)

	def update_metrics(self):
		raw_metrics = self._api.performance_collector.query_metrics_data(",".join((
			"CPU/Load/User",
			"CPU/Load/Kernel",
			"RAM/Usage/Used",
			"Net/Rate/Rx",
			"Net/Rate/Tx"
		)), [self._vbox])
		logging.info(raw_metrics)

				
#>>> c.setup_metrics("CPU/Load/User", [api.machines[0]], 1, 1)
#>>> c.enable_metrics("CPU/Load/User", [api.machines[0]])
#>>> c.query_metrics_data("CPU/Load/User", [api.machines[0]])
