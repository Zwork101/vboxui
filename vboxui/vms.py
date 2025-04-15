import logging
from .models import Metric

from textual.screen import Screen
from textual.widgets import Header, TabbedContent, TabPane
from vbox_api import VBoxAPI, models

from vboxui.instance import VM

class VMList(Screen):

	def __init__(self, api: VBoxAPI, *args, **kwargs):
		self.api = api

		self.vms: list[models.Machine] = api.machines

		for vm in self.vms:
			self.api.performance_collector.setup_metrics(None, vm, 2, 1)
			self.api.performance_collector.enable_metrics(None, vm)

		super().__init__(*args, **kwargs)

	def query_metrics(self):
		vm_summary = {}
		for vm in self.vms:
			vm_pane: VM = self.query("#ID" + vm.id).first(VM)
			raw_metrics = self.api.performance_collector.query_metrics_data(None, vm)
			summary = {}
			for name, _, unit, scale, _, _, _, value in zip(*(raw_metrics[key] for key in raw_metrics)):

				logging.info(f"{vm.name}, {name}, {value} / {scale} {unit}")

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
		with TabbedContent():
			for vm in self.vms:
				with TabPane(vm.name):
					yield VM(vm, self.api, id= "ID" + vm.id)

	def on_mount(self):
		self.title = "VBoxUI"
		self.set_interval(2, self.query_metrics)
