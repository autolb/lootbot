import os
import json
import asyncio

from bot import alemiBot

DEFAULTS = {
	# TODO move here default config
}

def _update_values(cfg:dict, src:dict) -> dict:
	if type(cfg) is not dict: # this is a config value, replace
		return src
	if type(src) is not dict: # nothing more to load
		return cfg
	for key in cfg:
		if key in src:
			cfg[key] = _update_values(cfg[key], src[key])
	return cfg

class ConfigLoader:
	async def unserialize(self) -> dict:
		raise NotImplementedError

	async def serialize(self, data:dict) -> bool:
		raise NotImplementedError
	
class FileLoader(ConfigLoader):
	def __init__(self, path:str):
		self.path = path

	async def userialize(self) -> dict:
		if not os.path.isfile(self.path):
			return {}
		with open(self.path) as f:
			return json.load(f)

	async def serialize(self, data:dict) -> bool:
		with open(self.path, "w") as f:
			json.dump(data, f)
		return True

class MessageLoader(ConfigLoader):
	def __init__(self, client, msg_id:int):
		self.msg_id = msg_id
		self.client = client

	async def unserialize(self) -> dict:
		msg = await self.client.get_messages("me", self.msg_id)
		if msg.empty:
			return {}
		return json.loads(msg.text)

	async def serialize(self, data:dict) -> bool:
		text = json.dumps(data, default=str)
		await self.client.edit_message_text("me", self.msg_id, text, parse_mode=None)
		return True

class ConfigHolder:
	def __init__(self):
		self.store : dict = DEFAULTS
		self.loader : ConfigLoader = None

	def load(self, data:dict):
		self.store = _update_values(self.store, data)

	async def serialize(self):
		await self.loader.serialize(self.store)

	async def unserialize(self):
		self.store = await self.loader.unserialize()

	def __getitem__(self, name:str) -> Any:
		return self.store[name]

	def __setitem__(self, name:str, value:Any):
		self.store[name] = value
		asyncio.create_task(self.loader.serialize(self.store)) # can't await here, do in background

CONFIG = ConfigHolder()

@alemiBot.on_ready()
async def load_config(client):
	loader = alemiBot.config.get("lbconfig", "loader", fallback="file").lower().strip()
	if engine == "file":
		path = alemiBot.config.get("lbconfig", "path", fallback="plugins/lootbot/data/config.json")
		CONFIG.loader = FileLoader(path)
	elif engine == "message":
		CONFIG.loader = MessageLoader(client, int(alemiBot.config.get("lbconfig", "msg_id")))
	else:
		raise ValueError("Invalid ConfigLoader type provided. Valid are ('file', 'message')")
	await CONFIG.unserialize()

