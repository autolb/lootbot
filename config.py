import os
import json

DEFAULTS = {
	# TODO move here default config
}

class ConfigEngine(object):
	def __init__(self):
		self.store = DEFAULTS

	def _update_values(self, cfg:dict, src:dict) -> dict:
		if type(cfg) is not dict: # this is a config value, replace
			return src
		if type(src) is not dict: # nothing more to load
			return cfg
		for key in cfg:
			if key in src:
				cfg[key] = self._update_values(cfg[key], src[key])
		return cfg

	def get(self) -> dict:
		return self.store

	async def unserialize(self) -> bool:
		raise NotImplementedError

	async def serialize(self) -> bool:
		raise NotImplementedError
	
class FileEngine(ConfigEngine):
	def __init__(self, path:str):
		self.path = path
		super().__init__()

	async def userialize(self):
		if not os.path.isfile(self.path):
			return False
		with open(self.path) as f:
			buf = json.load(f)
		self.store = self._update_values(self.store, buf)
		return True

	async def serialize(self):
		with open(self.path, "w") as f:
			json.dump(self.store, f)


class MessageEngine(ConfigEngine):
	def __init__(self, client, msg_id:int):
		self.msg_id = msg_id
		self.client = client
		super().__init__()

	async def unserialize(self) -> bool:
		msg = await self.client.get_messages("me", self.msg_id)
		if msg.empty:
			return False
		self.store = json.loads(msg.text)
		return True

	async def serialize(self) -> bool:
		data = json.dumps(self.store, default=str)
		await self.client.edit_message_text("me", self.msg_id, data, parse_mode=None)
		return True

# class ConfigDriver(object):
# 	def __init__(self):
# 		self.engine = alemiBot.config.get("lbconfig", "engine", fallback="file")

# 
# 	def 
# 
# # Config
# 
# 
# try:
# 	data = {} # Compatibility! Load also config from old location
# 	if os.path.isfile("plugins/lootbot/data/config.json"):
# 		with open("plugins/lootbot/data/config.json") as f:
# 			data = json.load(f)
# 	else:
# 		with open("data/lootcfg.json") as f:
# 			data = json.load(f)
# 	load_config(CONFIG, data)
# except:
# 	with open("plugins/lootbot/data/config.json", "w") as f:
# 		json.dump(CONFIG, f)