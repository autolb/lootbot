import asyncio
import random
import traceback
import json
import os # Temporary

from enum import Enum

# ids
LOOTBOT = 171514820
CRAFTLOOTBOT = 280391978
LOOTPLUSBOT = 42636063
MAPMATCHERBOT = 1541517339

# Config
CONFIG = {
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
		"safetime" : 5,			# Stop going next to zone when less than these many minutes are left
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

def load_config(cfg, src):
	if type(cfg) is not dict: # this is a config value, replace
		return src
	if type(src) is not dict: # nothing more to load
		return cfg
	for key in cfg:
		if key in src:
			cfg[key] = load_config(cfg[key], src[key])
	return cfg

try:
	data = {} # Compatibility! Load also config from old location
	if os.path.isfile("plugins/lootbot/data/config.json"):
		with open("plugins/lootbot/data/config.json") as f:
			data = json.load(f)
	else:
		with open("data/lootcfg.json") as f:
			data = json.load(f)
	load_config(CONFIG, data)
except:
	with open("plugins/lootbot/data/config.json", "w") as f:
		json.dump(CONFIG, f)

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

WAIT = CONFIG["wait"]
# Global utilities
async def random_wait(n=1):
	for _ in range(n):
		await asyncio.sleep(random.gauss(WAIT["gauss"]["mu"], WAIT["gauss"]["sigma"]) + 
							random.uniform(WAIT["uni"]["min"], WAIT["uni"]["max"]) +
							((random.uniform(0, 1)**WAIT["poly"]["exp"]) * WAIT["poly"]["coeff"]))
