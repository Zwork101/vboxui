from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Header, TabbedContent, TabPane
from vbox_api import VBoxAPI, models

from vboxui.instance import VM

class VMList(Screen):

	def __init__(self, api: VBoxAPI, *args, **kwargs):
		self.api = api

		self.vms: list[models.Machine] = api.machines

		super().__init__(*args, **kwargs)

	def compose(self):
		yield Header()
		with TabbedContent():
			for vm in self.vms:
				with TabPane(vm.name):
					yield VM(vm, self.api)

	def on_mount(self):
		self.title = "VBoxUI"

