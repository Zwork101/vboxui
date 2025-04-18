import asyncio
import logging
import time
from textual import on, work
from textual.css.query import NoMatches, TooManyMatches, WrongType

from vboxui.snapshots import ListSnapshots, TakeSnapshot
from .models import Metric

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Markdown, ProgressBar, Rule
from vbox_api.api import VBoxAPI
from vbox_api.models.machine import Machine, MachineHealth

class MetricDisplay(Container):

	CSS = """
	Vertical {
		align-content: middle center;
	}

	Vertical > * {
		height: 1fr;
	}

	MetricDisplay {
		border: round yellow;
	}
	"""

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
	DEFAULT_CSS = """
	.menu {
	  dock: left;
	  width: 25%;
	  height: 100%;
	  content-align: center middle;
	}

	.menu > Button {
		margin: 1;
		width: 80%;
	}

	.information {
	  width: 100%;
	  height: 100%;
	  border: round white;
	}

	.stats {
	  height: 6fr;
	}

	.stats > Vertical {
	  keyline: thin white;
	}

	.specs {
	  height: 4fr;
	  margin-bottom: 1;
	}

	MetricDisplay {
		height: 1fr;
		width: 1fr;
	}

	Rule {
		padding: 0;
	}

	"""

	metric_cpu_user_load = reactive(Metric(0.0, 100, "%"))
	metric_cpu_kernel_load = reactive(Metric(0.0, 100, "%"))
	metric_mem_usage = reactive(Metric(0, 100, "kB"))
	metric_disk_used = reactive(Metric(0, 1, "MB"))
	metric_network_rx = reactive(Metric(0.0, 1, "B/s"))
	metric_network_tx = reactive(Metric(0.0, 1, "B/s"))

	vbox_name = reactive("")
	vbox_cpu_count = reactive(0)
	vbox_memory = reactive(0)
	vbox_health = reactive(MachineHealth.ERROR)

	def __init__(self, machine: Machine, api: VBoxAPI, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._vbox = machine
		self._api = api
		self.set_reactive(self.__class__.vbox_name, machine.name)
		self.vbox_os: str = machine.os_type_id
		self.set_reactive(self.__class__.vbox_cpu_count, machine.cpu_count)
		self.set_reactive(self.__class__.vbox_memory, machine.memory_size)
		self.set_reactive(self.__class__.vbox_health, machine.health)  # pyright: ignore [reportArgumentType]
		self.vbox_networks = machine.network_adapters
		self.vbox_drives = []

		self._latest_state = machine.get_last_state_change_dt()
		self.set_interval(2, self.poll_status)

		for attachment in machine.mediums:
			if attachment.type == 'HardDisk':
				self.vbox_drives.append(attachment)

	def compose(self) -> ComposeResult:
		with Horizontal(classes="instance"):
			with Vertical(classes="menu"):
				yield Button("Start VM", variant="success", disabled=self.vbox_health == MachineHealth.RUNNING, id="start-btn")
				yield Button("Stop VM", variant="primary", disabled=self.vbox_health != MachineHealth.RUNNING, id='stop-btn')
				yield Button("VM Settings", variant="warning", disabled=True)
				yield Button("Take Snapshot", variant="warning", id="take-snap-btn")
				yield Button("Revert Snapshot", variant="warning", id="use-snap-btn")
				yield Button("Delete VM", variant="error", id="delete-btn", disabled=self.vbox_health == MachineHealth.RUNNING)
			with Vertical(classes="information"):
				with Horizontal(classes="specs"):
					with Vertical():
						yield Markdown(f"**Name:** {self.vbox_name}", id="vbox-name")
						yield Markdown(f"**Operating System:** {self.vbox_os}", id="vbox-os")
						status = MachineHealth._value2member_map_[self.vbox_health].name
						yield Markdown(f"**Health:** {status}", id="vbox-health")
					with Vertical():
						yield Markdown(f"**CPU Cores**: {self.vbox_cpu_count}", id="vbox-cores")
						yield Markdown(f"**Total Memory**: {self.vbox_memory} MB", id="vbox-memory")
						yield Markdown(f"**Test**: test")
				with Horizontal(classes="stats"):
					with Vertical():
						yield MetricDisplay("User CPU Usage", self.metric_cpu_user_load, id="cpu-user-metric")
						yield MetricDisplay("Kernel CPU Usage", self.metric_cpu_kernel_load, id="cpu-kernel-metric")
						yield MetricDisplay("RAM Usage (Guest Additions Required)", self.metric_mem_usage, id="mem-metric")
					with Vertical():
						yield MetricDisplay("Disk Usage", self.metric_disk_used, id="disk-metric")
						yield MetricDisplay("Network Rx Usage", self.metric_network_rx, id="net-rx-metric")
						yield MetricDisplay("Network Tx Usage", self.metric_network_tx, id="net-tx-metric")

	@on(Button.Pressed, "#use-snap-btn")
	@work()
	async def revert_snapshot(self):
		logging.info("Opening list")
		selected = await self.app.push_screen_wait(
			ListSnapshots(self._vbox)
		)
		if selected:
			with self._vbox.with_lock() as mut_machine:
				mut_machine.restore_snapshot(selected)
				for i in range(20):
					if mut_machine.health != MachineHealth.WARNING:
						break
					await asyncio.sleep(.5)
				else:
					raise TimeoutError("Unable to take snapshot")
			

	@on(Button.Pressed, "#start-btn")
	def start_vm(self):
		logging.info("Starting VM")
		self._vbox.start()
		self.query("#start-btn").only_one(Button).disabled = True
		self.query("#stop-btn").only_one(Button).disabled = False
		self.query("#delete-btn").only_one(Button).disabled = True

	@on(Button.Pressed, "#stop-btn")
	def stop_vm(self):
		logging.info("Stopping VM")
		self._vbox.stop()
		self.query("#start-btn").only_one(Button).disabled = False
		self.query("#stop-btn").only_one(Button).disabled = True
		self.query("#delete-btn").only_one(Button).disabled = False

	@on(Button.Pressed, "#delete-btn")
	def delete_vm(self):
		self._vbox.delete()
		self.parent.parent.parent.parent.vms.remove(self._vbox)  # pyright: ignore [reportOptionalMemberAccess, reportAttributeAccessIssue]
		self.parent.parent.parent.parent.refresh(layout=True, recompose=True)  # pyright: ignore [reportOptionalMemberAccess, reportAttributeAccessIssue]

	@on(Button.Pressed, "#take-snap-btn")
	@work()
	async def open_snap(self):
		await self.app.push_screen_wait(
			TakeSnapshot(self._vbox)
		)


	def poll_status(self):
		latest_state = self._vbox.get_last_state_change_dt()

		if latest_state > self._latest_state:
			self._latest_state = latest_state
			self.vbox_name = self._vbox.name
			self.vbox_cpu_count = self._vbox.cpu_count

			if self.vbox_health != MachineHealth.RUNNING and \
				self._vbox.health == MachineHealth.RUNNING:
				logging.info("Identified new status")
				logging.info(f"{self._api.performance_collector.setup_metrics(None, self._vbox, 2, 1)}")
				logging.info(f"{self._api.performance_collector.enable_metrics(None, self._vbox)}")

			self.vbox_health = self._vbox.health
			self.vbox_memory = self._vbox.memory_size

	def watch_vbox_name(self, name: str):
		self.query_exactly_one("#vbox-name", Markdown).update(f"**Name:** {name}")

	def watch_vbox_cpu_count(self, count: int):
		self.query_exactly_one("#vbox-cores", Markdown).update(f"**CPU Cores**: {count}")

	def watch_vbox_health(self, health: int):
		status = MachineHealth._value2member_map_[health].name
		self.query_exactly_one("#vbox-health", Markdown).update(f"**Health:** {status}")

		if health == MachineHealth.RUNNING:
			self.query("#start-btn").only_one(Button).disabled = True
			self.query("#stop-btn").only_one(Button).disabled = False
			self.query("#delete-btn").only_one(Button).disabled = True
		else:
			self.query("#start-btn").only_one(Button).disabled = False
			self.query("#stop-btn").only_one(Button).disabled = True
			self.query("#delete-btn").only_one(Button).disabled = False

	def watch_vbox_memory(self, memory: int):
		self.query_exactly_one("#vbox-memory", Markdown).update(f"**Total Memory**: {memory} MB")

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
