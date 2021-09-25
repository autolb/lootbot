import asyncio
import random
import logging
import json
import os

from enum import Enum
from typing import Union

from bot import alemiBot
from pyrogram import filters

# ids
LOOTBOT = "lootgamebot"
CRAFTLOOTBOT = "craftlootbot"
LOOTPLUSBOT = "lootplusbot"
MAPMATCHERBOT = "MapMatcher_bot"

# Priorities
class Priorities:
	map  : int = 47
	daily: int = 48
	event: int = 49
	norm : int = 50
	stats: int = 51
	cave : int = 52
	miss : int = 53
	insp : int = 54
	contr: int = 55
	dung : int = 56
	rand : int = 57
	craft: int = 58
	snow : int = 59
	last : int = 60 # Only for "clock" handler

# Config
DEFAULTS = {
	"gem-limit" : 50,		# If you have less gems than this, stops using them
	"sync" : {				# Fetch user info, very much still TODO
		"auto" : False,			# Do it automatically
		"offset" : 17,			# Do it this much after midnight
		"friends" : {			# Sync friends
			"auto" : False,			# Automatically download a friend list
			"url" : "",				# Download url, should be a list of names without @
		}
	},
	"log" : {				# Log certain events
		"pin" : {				# Pin events
			"craft" : True,			# Failed craft
			"death" : True,			# Death
			"spy" : True,			# Being spied
			"dm" : True,			# Direct Messages
			"reward" : True,		# Received something
			"map" : True			# Pin map results
		},
		"msg" : {				# Send events as messages
			"spy" : False,			# Log being spied
		},
		"group" : 0				# Group ID to log into
	},
	"talismani" : False,    # Use talismans. Turn off if you don't have them all!
	"mission" : {			# Do Missions
		"auto" : False,			# Restart mission automatically
		"skip" : False,			# Use gems to skip them
		"rarity" : "R"			# Skip missions with this or better rarity
	},
	"dungeon" : {			# Do dungeons
		"auto" : False,			# Run the dungeon automatically
		"start" : False,		# Start a new dungeon automatically
		"maledetto" : False,	# Prefer cursed dungeons, otherwise just pick 1st
		"varco" : False,		# Use a Varco to restart dungeons immediately (when possible)
		"hp" : 0.7,				# Heal when health is below this hp threshold (0.7 = 70%)
		"cariche" : 20,			# Start running dungeon again when you have at least these charges
		"concentrazioni" : 2,	# Concentrate this many times
		"meditazioni" : 2,		# Meditate this many times
		"polvere" : True,		# Stop to get dust
		"mob-prio" : False,		# Prefer mobs to other rooms
		"mapmatcher" : False,	# Send dungeon mapping to @MatMatcher_bot automatically
		"spell" : {				# Cast Spells
			"auto" : False,			# Do automatically in a fight
			"rateo" : [20, 15, 15], # Mana ratio to use to recraft spells
		},
		"incisioni" : True,		# Try unsure incisions
		"try-buttons" : True,	# Try all icy buttons
		"item" : "Pozione piccola", # Item to gift to Brucaliffo
		"kit" : {				# Sword thingy
			"farm" : True,			# Try to farm Kit Fuga
			"limit" : 3				# Stop at x% death rate
		},
	},
	"mappe" : {				# Do maps
		"auto" : False,			# Play automatically
		"prio" : False,			# Do maps as soon as available, might leave other tasks hanging
		"start" : False,		# Queue for a map as soon as possible
		"reque" : True,			# Put yourself in queue again if it expires, 
		"teleport" : False,		# Teleport to other players
		"attack" : False,		# Attack other players
		"friends" : {			# Behavior to use with friends
			"flee" : False,			# Flee from friends
			"limit" : 3,			# Don't flee if there are this or less player left ( <= )
		},
		"mapmatcher" : False,	# Automatically forward map to MapMatcher bot
		"ai" : {				# Parameters for the decision making "AI"
			"center-bias" : 0.5,	# Bias towards the center. If > 1, matters more than distance from the player. If < 0, keeps player away from center
			"base-mult" : 1.0,		# Multiplier for tile base value
			"objective" : 30,		# Points awarded to paths going towards objective
			"zigzag" : 10,			# Points awarded to paths going zig-zag
			"stationary" : 15,		# Points removed to paths not moving
			"zone" : 100,			# Points removed to paths going into incoming zone
			"avoid" : 50,			# Points removed to paths going on bad terrain
			"min-cariche-safe" : 2  # Stop counting corners as valid once you have less (or equal) than this threshold
		},
		"soglie" : {				# Thresholds for various choices
			"rottami" : 2,				# Don't buy with rottami if would leave with fewer rottami than this
			"centro-min" : 6,			# Min number of rottami to go to centro scambi
			"heal-cash" : 1000,			# Min money to try and go heal
			"hp-heal" : 3000,			# If fewer hp than this, go heal
			"hp-white" : 4000,			# If fewer hp than this, prefer white spaces (to heal)
			"shop-cash" : 2000,			# Min money to go to shop
			"hp-rottame" : 800,		   # Don't throw rottame in fight if enemy has fewer hp than this
		},
	},
	"ispezione" : {			# Do inspections
		"auto" : False,			# Restart automatically
		"mm" : True,			# Try to match with a worse player
		"reroll" : 20,			# Retry matchmaking up to this many times
		"keep" : 80.0			# Keep combinations with value >=
	},
	"contrabbandiere" : False,# Do Contrabbandiere
	"cava" : {				# Do Explorations
		"auto" : False,			# Restart automatically
		"name" : "Vesak",		# Do exploration containing this in its name
		"ritorna" : True,		# Return from exploration when possible
		"skip" : False,			# Use gems to conclude immediately
		"halvedskip" : False,	# Use gems to skip halved caves too
	},
	"incarichi" : {			# Do Incarichi
		"auto" : True			# Press buttons automatically
	},
	"raccogli" : False,		# Get random drops (boccetta cariche, extra mana...)
	"assalto" : {			# Do Assault
		"auto" : False,			# Automatically Increment
		"ruolo" : None			# Does nothing for now
	},
	"eventi" : {			# Try to do recurring events
		"generatore": {			# Do dust generator
			"auto": False,			# Automatically start and empty
			"min" : 10,				# Minimum amount of dust to trigger an empty
			"maxt" : 600			# Max seconds elapsed since last tick to trigger an empty
		},
		"miniera": {			# Do Mana Mines
			"auto" : False,			# Automatically start and choose
			"lower" : False			# Prefer mana wich reserve is the lowest rather than most productive
		},
		"itinerario" : {		# Do Itineraries
			"auto" : False,			# Automatically restart
			"zone" : "Carro Abbandonato", # Which one to do
		},
		"ricercato" : {			# Do Wanted manhunts
			"auto" : False,			# Automatically start
		},
	},
	"imprese" : {			# Do dailies
		"auto" : False,			# Try to complete dailies by overruling config
		"wait-failed" : False,	# Stop when a craft fails, instead of skipping it
		"single" : False,		# Do "single task" dailies
		"activity" : False		# Do activities (mission, cave, dungeon) for dailies
	},
	"wait" : {				# Fine tune the random waits
		"forward-cd" : 3.5,		# Wait this much when doing "full zaino"
		"forzieri-cd" : 7.5,	# Wait this much to buy chests
		"uni" : {				# A linear random value
			"min" : 0.75,			# min value
			"max" : 2.25			# max value
		},
		"gauss" : {				# A Gaussian random value
			"mu" : 1.0,				# gaussian mean (center)
			"sigma" : 0.25			# gaussian variance
		},
		"poly" : {				# A polynomial random value
			"exp" : 8,				# Exponent value
			"coeff" : 20.0			# Coefficient value
		},
	},
	"night" : False,		# no tasks can be added to the loop at night
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
	"""Abstract implementation of a config loader. Must provide async serialize and unserialize"""
	async def unserialize(self) -> dict:
		raise NotImplementedError

	async def serialize(self, data:dict) -> bool:
		raise NotImplementedError
	
class FileLoader(ConfigLoader):
	"""Load and store config in a file on local filesystem. Path can be specified"""
	def __init__(self, path:str):
		self.path = path

	async def unserialize(self) -> dict:
		if not os.path.isfile(self.path):
			return {}
		with open(self.path) as f:
			return json.load(f)

	async def serialize(self, data:dict) -> bool:
		with open(self.path, "w") as f:
			json.dump(data, f)
		return True

class MessageLoader(ConfigLoader):
	"""Load and store config in a telegram message.
	You should only use saved messages or channels since they can be edited forever.
	Using a group or direct message will break changing config, but will load fine.
	Needs a known message_id at least"""
	def __init__(self, client, msg_id:int, chan:Union[str,int]="me"):
		self.msg_id = msg_id
		self.chan = int(chan) if chan.isnumeric() else chan
		self.client = client

	async def unserialize(self) -> dict:
		msg = await self.client.get_messages(self.chan, self.msg_id)
		if msg.empty:
			return {}
		return json.loads(msg.text)

	async def serialize(self, data:dict) -> bool:
		text = json.dumps(data, default=str)
		await self.client.edit_message_text("me", self.msg_id, text, parse_mode=None)
		return True

class MapTile(Enum):
	scrigno = "💰"
	rottame = "🔩"
	impulso = "✨"
	carica = "🔋"
	scontro = "💥"
	farmacia = "💊"
	emporio = "💸"
	centro = "🔁"
	teletrasporto = "💨"
	ignoto = "◼️"
	vuoto = "◻️"
	avversario = "👣"
	stun = "⚡️"
	trappola = "🕳"
	morte ="☠️"

class Rarity(Enum):
	IN = 999
	X = 10
	U = 9	
	S = 8
	UE = 7
	E = 6
	L = 5
	UR = 4
	R = 3
	NC = 2
	C = 1
	def __lt__(self, other):
		return self.value < other.value
	def __le__(self, other):
		return self.value <= other.value
	def __gt__(self, other):
		return self.value > other.value
	def __ge__(self, other):
		return self.value >= other.value
	def __eq__(self, other):
		return self.value == other.value
	def __ne__(self, other):
		return self.value != other.value


class ConfigHolder:
	"""A wrapper to hold the config data and loader

	Serialize and unserialize can be called directly on this without args.
	Calling the config holder itself will return the config dictionary"""
	def __init__(self):
		self.store : dict = DEFAULTS
		self.loader : ConfigLoader = None

	def __call__(self) -> dict:
		return self.store

	def update(self, data:dict):
		self.store = _update_values(self.store, data)

	async def serialize(self):
		await self.loader.serialize(self.store)

	async def unserialize(self):
		self.update(await self.loader.unserialize())

	def __str__(self) -> str:
		return str(self.store)

CONFIG = ConfigHolder()

@alemiBot.on_client_status(filters.client_ready)
async def load_config(client, status_update):
	loader = alemiBot.config.get("lbconfig", "loader", fallback="file").lower().strip()
	logging.info("Loading config with loader '%s'", loader)
	if loader == "message":
		CONFIG.loader = MessageLoader(
			client,
			int(alemiBot.config.get("lbconfig", "msg_id")),
			alemiBot.config.get("lbconfig", "chan_id", fallback="me")
		)
	else: # file is default loader
		if loader != "file":
			logging.error("Invalid ConfigLoader type provided, defaulting to 'file'. Valid are ('file', 'message')")
		CONFIG.loader = FileLoader(
			alemiBot.config.get("lbconfig", "path", fallback="plugins/lootbot/data/config.json")
		)
	await CONFIG.unserialize()

# Global utilities
async def random_wait(n=1):
	for _ in range(n):
		await asyncio.sleep(
			random.gauss(CONFIG()["wait"]["gauss"]["mu"], CONFIG()["wait"]["gauss"]["sigma"]) + 
			random.uniform(CONFIG()["wait"]["uni"]["min"], CONFIG()["wait"]["uni"]["max"]) +
			((random.uniform(0, 1)**CONFIG()["wait"]["poly"]["exp"]) * CONFIG()["wait"]["poly"]["coeff"])
		)
