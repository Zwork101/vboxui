import logging
from textual.css.query import NoMatches, TooManyMatches, WrongType
from .models import Metric

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Markdown, ProgressBar
from vbox_api.api import VBoxAPI
from vbox_api.models.machine import Machine, MachineHealth

class MetricDisplay(Container):

	metric = reactive(Metric(0, 1, "Unknown"))

	def __init__(self, name: str, metric: Metric, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.metric = metric
		self.metric_name = name

	def watch_metric(self, metric: Metric):
		try:
			value = self.query(".metric-value").first()
		except NoMatches:
			return

		if isinstance(value, Markdown):
			value.update(f"**{self.metric.value} {self.metric.unit}**")
		elif isinstance(value, ProgressBar):
			value.update(progress=metric.value, total=metric.scale)

	def compose(self) -> ComposeResult:
		with Vertical():
			yield Markdown(self.metric_name)
			if self.metric.scale == 1:
				yield Markdown(f"**{self.metric.value} {self.metric.unit}**", classes="metric-value")
			else:
				yield ProgressBar(self.metric.scale, show_eta=False, classes="metric-value")


class VM(Container):
	"""
	.menu {
	  dock: left;
	  width: 20%;
	  height: 100%;
	  border: 1px red solid;
	}

	.information {
	  width: 80%;
	  height: 100%;
	  border: 1px blue solid;
	}
	"""

	metric_cpu_user_load = reactive(Metric(0.0, 100, "%"))
	metric_cpu_kernel_load = reactive(Metric(0.0, 100, "%"))
	metric_mem_usage = reactive(Metric(0, 100, "kB"))
	metric_disk_used = reactive(Metric(0, 1, "MB"))
	metric_network_rx = reactive(Metric(0.0, 1, "B/s"))
	metric_network_tx = reactive(Metric(0.0, 1, "B/s"))

	def __init__(self, machine: Machine, api: VBoxAPI, *args, **kwargs):
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

		super().__init__(*args, **kwargs)

	def compose(self) -> ComposeResult:
		with Horizontal(classes="instance"):
			with Vertical(classes="menu"):
				yield Button("Start VM", variant="success", disabled=self.vbox_health != MachineHealth.RUNNING)
				yield Button("Stop VM", variant="primary", disabled=self.vbox_health == MachineHealth.RUNNING)
				yield Button("VM Settings", variant="warning")
				yield Button("Take Snapshot", variant="warning")
				yield Button("Delete VM", variant="error")
			with Container(classes="information"):
				with Vertical():
					with Horizontal():
						with Vertical():
							yield Markdown(f"**Name:** {self.vbox_name}")
							yield Markdown(f"**Operating System:** {self.vbox_os}")
							yield Markdown(f"**Health:** {self.vbox_health}")
						with Vertical():
							yield Markdown(f"**Test**: test")
							yield Markdown(f"**Test**: test")
							yield Markdown(f"**Test**: test")
					with Horizontal():
						with Vertical():
							yield MetricDisplay("User CPU Usage", self.metric_cpu_user_load, id="cpu-user-metric")
							yield MetricDisplay("Kernel CPU Usage", self.metric_cpu_kernel_load, id="cpu-kernel-metric")
							yield MetricDisplay("RAM Usage (Guest Additions Required)", self.metric_mem_usage, id="mem-metric")
						with Vertical():
							yield MetricDisplay("Disk Usage", self.metric_disk_used, id="disk-metric")
							yield MetricDisplay("Network Rx Usage", self.metric_network_rx, id="net-rx-metric")
							yield MetricDisplay("Network Tx Usage", self.metric_network_tx, id="net-tx-metric")

	def watch_metric_cpu_user_load(self, metric: Metric):
		try:
			m_display: MetricDisplay = self.query("#cpu-user-metric").only_one(MetricDisplay)
			m_display.metric = metric
		except WrongType:
			logging.error("Found metric, but wrong Widget type")
		except (NoMatches, TooManyMatches):
			pass

	def watch_metric_cpu_kernel_load(self, metric: Metric):
		try:
			m_display: MetricDisplay = self.query("#cpu-kernel-metric").only_one(MetricDisplay)
			m_display.metric = metric
		except WrongType:
			logging.error("Found metric, but wrong Widget type")
		except (NoMatches, TooManyMatches):
			pass

	def watch_metric_mem_usage(self, metric: Metric):
		try:
			m_display: MetricDisplay = self.query("#mem-metric").only_one(MetricDisplay)
			m_display.metric = metric
		except WrongType:
			logging.error("Found metric, but wrong Widget type")
		except (NoMatches, TooManyMatches):
			pass

	def watch_metric_disk_used(self, metric: Metric):
		try:
			m_display: MetricDisplay = self.query("#disk-metric").only_one(MetricDisplay)
			m_display.metric = metric
		except WrongType:
			logging.error("Found metric, but wrong Widget type")
		except (NoMatches, TooManyMatches):
			pass

	def watch_metric_network_rx(self, metric: Metric):
		try:
			m_display: MetricDisplay = self.query("#net-rx-metric").only_one(MetricDisplay)
			m_display.metric = metric
		except WrongType:
			logging.error("Found metric, but wrong Widget type")
		except (NoMatches, TooManyMatches):
			pass

	def watch_metric_network_tx(self, metric: Metric):
		try:
			m_display: MetricDisplay = self.query("#net-rx-metric").only_one(MetricDisplay)
			m_display.metric = metric
		except WrongType:
			logging.error("Found metric, but wrong Widget type")
		except (NoMatches, TooManyMatches):
			pass

				
#>>> c.setup_metrics("CPU/Load/User", [api.machines[0]], 1, 1)
#>>> c.enable_metrics("CPU/Load/User", [api.machines[0]])
#>>> c.query_metrics_data("CPU/Load/User", [api.machines[0]])
