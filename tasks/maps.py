"""
Automatically do Lootbot maps
"""
import re
import logging

from pyrogram import filters

from bot import alemiBot

from util.permission import is_superuser
from util.command import filterCommand
from util.message import edit_or_reply
from util.decorators import report_error, set_offline

from plugins.lootbot.common import LOOTBOT, MAPMATCHERBOT, random_wait, CONFIG, Priorities as P
from plugins.lootbot.tasks import si, no, mnu
from plugins.lootbot.loop import LOOP, create_task

logger = logging.getLogger(__name__)

TILES = {
	"GET" : ["💰", "🔩", "✨", "🔋", "💥"],
	"COND" : ["💊", "💸", "🔁"],
	"OTHER" : ["💨", "◼️", "◻️"],
	"AVOID" : ["👣", "⚡️", "🕳", "☠️"],
	"PRIORITY" : [ "💰", "🔩", "✨", "🔋", "💥", "◼️", "💊", "💸", "🔁", "💨", "◻️", "👣", "🕳", "⚡️", "☠️"]
}

def update_board(old, new):
	"""Changes unexplored tiles with explored ones, remembering progress"""
	for i in range(min(len(old), len(new))):
		for j in range(min(len(old[i]), len(new[i]))):
			if new[i][j] not in ["◼️", "📍"]:
				old[i][j] = new[i][j]
			elif old[i][j] in ["👣", "💥"]:
				old[i][j] = new[i][j]

def dist(player, loc): # This is not an euclidean distance! It's discrete
	"""Calculate distance across 2 locations: it counts how many movements you need to reach it"""
	return abs(player[0] - loc[0]) + abs(player[1] - loc[1])

def b_dist(pl, loc): # biased towards the center
	return dist(pl, loc) + (dist((4, 4), loc) * CONFIG()["mappe"]["ai"]["center-bias"])

def seek_player(board):
	for i, row in zip(range(len(board)), board):
		if "📍" in row:
			return (i, row.index("📍"))
	return (-1, -1)

def next_to_zone(loc, board):
	if loc[0] == 0 or loc[0] == 8 or loc[1] == 0 or loc[1] == 8 \
	or board[loc[0]+1][loc[1]] == "☠️" \
	or board[loc[0]-1][loc[1]] == "☠️" \
	or board[loc[0]][loc[1]+1] == "☠️" \
	or board[loc[0]][loc[1]-1] == "☠️":
		return True
	return False

def vec_to_char(vin):
	if vin == (0, -1):
		return "⬅️"
	if vin == (0, 1):
		return "➡️"
	if vin == (-1, 0):
		return "⬆️"
	if vin == (1, 0):
		return "⬇️"
	if vin == (0, 0):
		return "🖐 Controlla"

def char_to_vec(c):
	if c == "⬇️":
		return (1, 0)
	if c == "⬆️":
		return (-1, 0)
	if c == "⬅️":
		return (0, -1)
	if c == "➡️":
		return (0, 1)
	return (0, 0)

def calc_player_move(pl, vin):
	return (pl[0] + vin[0] , pl[1] + vin[1])

def pathfind(pl, dest, board, priority, safe=False): 
	delta = (pl[0] - dest[0], pl[1] - dest[1])
	avail = []
	for i, j in [ (1, 0), (0, 1), (-1, 0), (0, -1), (0, 0) ]:
		if pl[0] + i >= 0 and pl[0] + i <= 8 \
		and pl[1] + j >= 0 and pl[1] + j <= 8 :
			pos = (pl[0] + i, pl[1] + j)
			tile = board[pos[0]][pos[1]]
			if tile == "☠️": # Literally can't walk on them
				continue
			score = (len(priority) - priority.index(tile)) * CONFIG()["mappe"]["ai"]["base-mult"]
			if safe and next_to_zone(pos, board):
				score -= CONFIG()["mappe"]["ai"]["zone"]
				if i == 0 and j == 0:
					score -= 3 * CONFIG()["mappe"]["ai"]["avoid"] # extra malus points for standing still next to zone
			if i == 0 and j == 0:
				score -= CONFIG()["mappe"]["ai"]["stationary"]
			if b_dist((pl[0] + i, pl[1] + j) , dest) < b_dist(pl, dest):
				score += CONFIG()["mappe"]["ai"]["objective"]
			elif b_dist((pl[0] + i, pl[1] + j), dest) > b_dist(pl, dest):
				score -= CONFIG()["mappe"]["ai"]["objective"]
			if (abs(delta[0]) > abs(delta[1]) and abs(i) > abs(j)) \
			or (abs(delta[0]) < abs(delta[1]) and abs(i) < abs(j)):
				score += CONFIG()["mappe"]["ai"]["zigzag"]
			if tile in TILES["AVOID"]:
				score -= CONFIG()["mappe"]["ai"]["avoid"]
			avail.append(((i, j), score))
	avail.sort(key=lambda x: x[1], reverse=True)
	return vec_to_char(avail[0][0])

class Destinations(dict):
	def __init__(self, board, pl, safe=False):
		super().__init__(self)
		for i, row in zip(range(len(board)), board):
			for j, tile in zip(range(len(row)), row):
				if tile != "☠️" and tile != "📍" and (not safe or not next_to_zone((i, j), board)):
					if tile not in self or b_dist(pl, (i,j)) < b_dist(pl, self[tile]):
						if (i, j) != pl or tile in ["💊", "💸", "🔁"]:
							self[tile] = (i,j)

# Requires client
async def torna_mappa(ctx):
	ctx.state["map"]["running"] = True
	await ctx.client.send_message(LOOTBOT, "Torna alla mappa")

# Requires client
async def apri_mappa(ctx):
	await ctx.client.send_message(LOOTBOT, "Mappe di Lootia 🗺 (Beta)")

# Requires client, direction
async def move_mappa(ctx):
	ctx.state["map"]["player"] = calc_player_move(ctx.state["map"]["player"], char_to_vec(ctx.direction))
	logger.info("Moving on map, destination : %s", ctx.state['map']['dest'])
	await ctx.client.send_message(LOOTBOT, ctx.direction)

# Show current map state
@alemiBot.on_message(is_superuser & filterCommand(["lmap"], list(alemiBot.prefixes), flags=["-list"]))
@report_error(logger)
@set_offline
async def show_map_command(client, message):
	out = ""
	if LOOP.state["map"]["board"] == {}:
		out = "`[!] → ` No board in memory"
	else:
		mapstate = LOOP.state["map"]
		chosen_dest = "N/A"
		if mapstate["locations"] and mapstate["dest"] and mapstate["dest"] in mapstate["locations"]:
			chosen_dest = f"{mapstate['dest']} : `{mapstate['locations'][mapstate['dest']]}`"
		out += f"`→ ` Destination : {chosen_dest}\n"
		if message.command["-list"]:
			out += f"` → ` 📍 : `{mapstate['player']}`\n"
			for loc in mapstate["locations"]:
				out += f"` → ` {loc} : `{mapstate['locations'][loc]}`\n"
		for i, row in zip(range(len(mapstate["board"])), mapstate["board"]):
			for j, cell in zip(range(len(row)), row):
				if not mapstate["dead"] and (i,j) == mapstate["player"]:
					out += "📍 "
				else:
					out += cell + " "
			out += "\n"
		out += f"❤️ {mapstate['hp']} 🔩 {mapstate['rottami']} 💰 {mapstate['cash']}\n"
		out += f"👥 {mapstate['opponents']['left']} 👣 {mapstate['cariche']} ☠️ {mapstate['zone-time']} min"
		# # would be cool to show this but it's not really kept up-to-date
		# for gear in mapstate["inventory"]:
		#	  out += f"` · ` {gear}\n"
	await edit_or_reply(message, out)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"La partita (?:di allenamento |)è terminata!"), group=P.map)
async def on_map_finished(client, message):
	if CONFIG()["log"]["pin"]["map"]:
		await message.pin()

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.me & filters.regex(pattern=r"Allenamento 🥋|Accedi alla Lobby 🏹"), group=P.map)
async def starting_map(client, message):
	LOOP.state["map"]["train"] = message.text == "Allenamento 🥋"

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Il tempo di ricerca nella lobby è scaduto, accedi di nuovo!"), group=P.map)
async def lobby_expired(client, message):
	if CONFIG()["mappe"]["reque"]:
		@create_task("Rientra in Lobby Mappe", client=client, train=bool(LOOP.state["map"]["train"]))
		async def reque_map(ctx):
			await apri_mappa(ctx)
			await random_wait()
			if ctx.train:
				await ctx.client.send_message(LOOTBOT, "Allenamento 🥋")
			else:
				await ctx.client.send_message(LOOTBOT, "Accedi alla Lobby 🏹")
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(reque_map)

MAIN_MENU_CHECK = re.compile(r"🗺 Puoi esplorare le Mappe(?: \(☠️ (?P<time>.*)\)|)")
@alemiBot.on_message(filters.chat(LOOTBOT) &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=P.map)
async def main_menu_trigger(client, message):
	LOOP.state["map"]["running"] = False
	match = MAIN_MENU_CHECK.search(message.text)
	if len(LOOP) < 1 and CONFIG()["mappe"]["auto"] and match:
		if match["time"]:
			LOOP.add_task(create_task("Mappa in attesa", client=client)(apri_mappa))
		elif CONFIG()["mappe"]["start"]:
			@create_task("Rientra in Lobby Mappe", client=client)
			async def start_map(ctx):
				await apri_mappa(ctx)
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Accedi alla Lobby 🏹")
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(start_map)
			LOOP.state["map"]["train"] = False

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Esplorazione mappa in corso!"), group=P.map)
async def why_2_steps_to_open_map_ffs(client, message):
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("Torna alla mappa", client=client)(torna_mappa))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"La mappa si è ristretta e le Cariche Movimento sono state ripristinate!"), group=P.map)
async def map_ready(client, message):
	if CONFIG()["mappe"]["auto"]:
		if not CONFIG()["mappe"]["prio"]:
			LOOP.state["dungeon"]["interrupt"] = True
		LOOP.add_task(create_task("Torna alla mappa", client=client)(torna_mappa), prio=CONFIG()["mappe"]["prio"])

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai terminato le mosse a disposizione, attendi il prossimo restringimento"), group=P.map)
async def no_more_moves(client, message):
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("Finite le mosse", client=client)(mnu), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"La mappa è stata generata!"), group=P.map)
async def map_generated(client, message):
	LOOP.state["map"]["hp"] = 5000
	LOOP.state["map"]["cash"] = 0
	LOOP.state["map"]["rottami"] = 0
	LOOP.state["map"]["board"] = {}
	LOOP.state["map"]["dead"] = False
	LOOP.state["map"]["once"] = True
	LOOP.state["map"]["cariche"] = 10
	if CONFIG()["mappe"]["auto"]:
		@create_task("'Vai in battaglia' lmao larpa meno edo dioporco", client=client)
		async def start_map(ctx):
			await ctx.client.send_message(LOOTBOT, "Vai in battaglia")
		if not CONFIG()["mappe"]["prio"]:
			LOOP.state["dungeon"]["interrupt"] = True
		LOOP.add_task(start_map, prio=CONFIG()["mappe"]["prio"])

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.me & filters.regex(pattern=r"Torna alla mappa"), group=P.map)
async def manual_map_open(client, message): # This is needed to set map as running in case user is playing manually
	LOOP.state["map"]["running"] = True

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.me & filters.regex(pattern=r"^(?:⬆️|⬇️|⬅️|➡️)$"), group=P.map)
async def manual_map_move(client, message): # This is needed to set map as running in case user is playing manually
	if LOOP.state["map"]["running"]:
		logger.info("Player moved manually in map : %s", message.text)
		LOOP.state["map"]["player"] = calc_player_move(LOOP.state["map"]["player"], char_to_vec(message.text))

STATUS_CHECK = re.compile(r"👥 (?P<left>[0-9]+) su (?P<max>[0-9]+) sopravvissuti\n❤️ (?P<hp>[0-9\.]+)\n👣 (?:(?P<cariche>[0-9]+) caric(?:he|a)|Cariche esaurite)\n(?:☠️ (?:meno di |)(?P<time>[0-9]+) minut(?:o|i)\n|)(?:🔋 (?P<boost>[0-9]+)\n|)\n(?P<board>[📍◼️◻️💰🕳💊🔁💸✨👣🔩☠️💨⚡️🔋💥 \n]+)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"👥 (?P<left>[0-9]+) su (?P<max>[0-9]+) sopravvissuti"), group=P.map)
async def map_screen(client, message):
	match = STATUS_CHECK.search(message.text)
	mapstate = LOOP.state["map"]
	if LOOP.state["map"]["once"]:
		LOOP.state["map"]["once"] = False
		if CONFIG()["mappe"]["mapmatcher"]:
			message.forward(MAPMATCHERBOT)
	if match:
		mapstate["opponents"]["left"] = int(match["left"])
		mapstate["opponents"]["max"] = int(match["max"])
		mapstate["hp"] = int(match["hp"].replace(".", ""))
		b = [ row.split() for row in match["board"].split("\n") ]
		pl = seek_player(b)
		if mapstate["board"] != {}:
			update_board(mapstate["board"], b)
		else:
			b[pl[0]][pl[1]] = "◻️" # Clear 1st pin
			mapstate["board"] = b
		mapstate["player"] = pl
		mapstate["locations"] = Destinations(mapstate["board"], pl, safe=mapstate["safe"])
		mapstate["zone-time"] = int(match["time"])
		if match["cariche"]:
			mapstate["cariche"] = int(match["cariche"])
			mapstate["safe"] = mapstate["cariche"] <= CONFIG()["mappe"]["ai"]["min-cariche-safe"]
		else:
			mapstate["cariche"] = 0
			mapstate["safe"] = True
	if CONFIG()["mappe"]["auto"]:
		board = mapstate["board"]
		pl = mapstate["player"]
		locations = mapstate["locations"]
		prio = [ "☠️", "⚡️", "🕳", "👣", "◼️", "💨", "🔁", "💸", "💊", "◻️", "💥", "🔋", "✨", "🔩", "💰" ] \
				if mapstate["hp"] < CONFIG()["mappe"]["soglie"]["hp-white"] else \
				 [ "☠️", "⚡️", "🕳", "👣", "◻️", "💨", "🔁", "💸", "💊", "◼️", "💥", "🔋", "✨", "🔩", "💰" ]
		if CONFIG()["mappe"]["attack"]:
			prio.remove("👣")
			prio.append("👣")
		if mapstate["cariche"] < 1: # Out of moves
			return LOOP.add_task(create_task("Finite mosse mappa", client=client)(mnu), prio=True)
		if mapstate["cash"] == {} or mapstate["rottami"] == {} or mapstate["just-killed"]:
			@create_task("Controlla sacca", client=client)
			async def check_bag(ctx):
				await ctx.client.send_message(LOOTBOT, "🛠 Sacca")
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(check_bag, prio=True)
			LOOP.state["map"]["just-killed"] = False
			LOOP.state["map"]["dead"] = False
			return
		if mapstate["controlla"]:
			@create_task("Controlla casella", client=client)
			async def check_tile(ctx):
				await ctx.client.send_message(LOOTBOT, "🖐 Controlla")
			LOOP.add_task(check_tile, prio=True)
			LOOP.state["map"]["controlla"] = False
			return
		if not match["time"]:
			return # Map is already just 1 cell in the center, don't even try to move!
		# Priority is: HEAL, LOOT, BUY, UNEXPLORED, EXPLORED
		pl = mapstate["player"]
		if mapstate["hp"] < CONFIG()["mappe"]["soglie"]["hp-heal"] and mapstate["cash"] >= CONFIG()["mappe"]["soglie"]["heal-cash"] and "💊" in locations:
			mapstate["dest"] = "💊"
			prio.remove("💊") or prio.append("💊")
			mov = pathfind(pl, locations["💊"], board, prio, safe=mapstate["safe"])
			return LOOP.add_task(create_task("Go to farmacia", client=client, direction=mov)(move_mappa), prio=True)
		mapstate["cariche"] -= 1
		# TODO go to closest of these, not to the highest prio one
		for sym in TILES["GET"]:
			if sym in locations:
				mapstate["dest"] = sym
				return LOOP.add_task(create_task("Raccogli loot (mappa)", client=client,
								direction=pathfind(pl, locations[sym], board, prio, safe=mapstate["safe"]))(move_mappa), prio=True)
		if mapstate["cash"] >= CONFIG()["mappe"]["soglie"]["shop-cash"] and "💸" in locations:
			mapstate["dest"] = "💸"
			return LOOP.add_task(create_task("Go to emporio (mappa)", client=client,
											direction=pathfind(pl, locations["💸"], board, prio, safe=mapstate["safe"]))(move_mappa), prio=True)
		if mapstate["rottami"] >= CONFIG()["mappe"]["soglie"]["centro-min"] and "🔁" in locations:
			mapstate["dest"] = "🔁"
			return LOOP.add_task(create_task("Go to centro scambi (mappa)", client=client,
											direction=pathfind(pl, locations["🔁"], board, prio, safe=mapstate["safe"]))(move_mappa), prio=True)
		# If there's nowhere to go, just go towards the center
		if mapstate["hp"] < CONFIG()["mappe"]["soglie"]["hp-white"] and "◻️" in locations: # If low, prefer explored spaces to heal!
			mapstate["dest"] = "◻️"
			return LOOP.add_task(create_task("Muoviti su spazi bianchi (mappa)", client=client,
											direction=pathfind(pl, locations["◻️"], board, prio, safe=mapstate["safe"]))(move_mappa), prio=True)
		if "◼️" in locations:
			mapstate["dest"] = "◼️"
			return LOOP.add_task(create_task("Muoviti su spazi neri (mappa)", client=client,
											direction=pathfind(pl, locations["◼️"], board, prio, safe=mapstate["safe"]))(move_mappa), prio=True)
		# Already visited whole map????
		mapstate["dest"] = "????"
		return LOOP.add_task(create_task("Muoviti dove cazzo capita dio porco", client=client,
										direction=pathfind(pl, (4, 4), board, prio, safe=mapstate["safe"]))(move_mappa), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Calpesti uno strano pulsante che emana un'onda di energia"), group=P.map)
async def impulse_shows_map(client, message):
	b = LOOP.state["map"]["board"]
	pl = LOOP.state["map"]["player"]
	b[pl[0]][pl[1]] = "◻️"
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("Impulso! Riguarda la mappa", client=client)(torna_mappa), prio=True)

ROTTAME_CHECK = re.compile(r"🔩 Rottame")
CASH_CHECK = re.compile(r"(?P<n>[0-9\.]+) §")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Cadi in una 🕳 Trappola e perdi|" +
			r"Qui non c'è nulla! Prosegui la tua esplorazione|" +
			r"Hai trovato uno 💰 Scrigno (?:Epico |)con al suo interno|" +
			r"Hai trovato uno Strano Congegno con al suo interno un 🔩 Rottame|" +
			r"Trovi e raccogli una 🔋 Bevanda Boost|" +
			r"Cadi in un ⚡️ Campo Paralizzante e vieni immobilizzato"
), group=P.map)
async def nothing_to_do_here(client, message):
	if ROTTAME_CHECK.search(message.text):
		if LOOP.state["map"]["rottami"] == {}:
			LOOP.state["map"]["rottami"] = 0
		LOOP.state["map"]["rottami"] += message.text.count("🔩 Rottame")
	if CASH_CHECK.search(message.text):
		if LOOP.state["map"]["cash"] == {}:
			LOOP.state["map"]["cash"] = 0
		LOOP.state["map"]["cash"] += int(CASH_CHECK.search(message.text)["n"].replace(".", ""))
	b = LOOP.state["map"]["board"]
	pl = LOOP.state["map"]["player"]
	if message.text.startswith("Cadi in una 🕳 Trappola"):
		b[pl[0]][pl[1]] = "🕳"
	else:
		b[pl[0]][pl[1]] = "◻️"
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("Niente da fare qui", client=client)(torna_mappa), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex("Decidi di scappare dallo scontro!"), group=P.map)
async def flee_from_combat(client, message):
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("Scappato dallo scontro", client=client)(torna_mappa), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(".*(?:Vieni|Venendo) sconfitto definitivamente con un colpo mortale!"), group=P.map)
async def got_killed(client, message):
	LOOP.state["map"]["dead"] = True
	board = LOOP.state["map"]["board"]
	pl = LOOP.state["map"]["player"]
	board[pl[0]][pl[1]] = "⚰️"
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("Sconfitto nelle mappe!", client=client)(mnu), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Hai incontrato un altro giocatore!\nScambi uno sguardo di sfida a (?P<name>[^ ]+) e ti prepari al duello!|" +
			r"L'avversario tenta di scappare dallo scontro senza successo|"
			r"Vieni colpito dall'avversario subendo|" +
			r"Riesci a schivare l'attacco|" +
			r"Il tempo per il turno dell'avversario è scaduto|" +
			r"L'avversario si mette in posizione difensiva|" +
			r"L'avversario inizia a caricare l'attacco!|" +
			r"Battaglia in corso!"
), group=P.map)
async def go_to_fight(client, message):
	b = LOOP.state["map"]["board"]
	pl = LOOP.state["map"]["player"]
	b[pl[0]][pl[1]] = "◻️"
	if CONFIG()["mappe"]["auto"]:
		@create_task("Vai al combattimento", client=client)
		async def goto_fight(ctx):
			await ctx.client.send_message(LOOTBOT, "Attacca!")
		LOOP.add_task(goto_fight, prio=CONFIG()["mappe"]["prio"])
		if not CONFIG()["mappe"]["prio"]:
			LOOP.state["dungeon"]["interrupt"] = True

ROTTAME_BOTTONE_CHECK = re.compile(r"🔩 Rottame \((?P<n>[0-9]+)\)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Stai combattendo contro (?P<user>[^ ]+) (?P<class>[🦊🐅🐲🦍🦅🕊🦏🦉🐓]+)\n" +
			r"(?:❤️|🧡|🖤) (?P<opphp>[0-9\.]+) hp\n" +
			r"(?P<weapon>.*)\n" +
			r"(?P<armor>.*)\n" +
			r"(?P<shield>.*)\n" +
			r"(?:🔗 Flaridion: (?P<flari>.*)|)\n" +
			r"\nLa tua salute: (?P<myhp>[0-9\.]+) hp"
), group=P.map)
async def fight_screen(client, message):
	m = message.matches[0]
	mapstate = LOOP.state["map"]
	mapstate["enemy"] = {
		"name" : m["user"],
		"class" : m["class"],
		"hp" : int(m["opphp"].replace(".", "")),
		"equip" : [ m["weapon"], m["armor"], m["shield"] ],
		"flaridion" : m["flari"] if m["flari"] else "N/A"
	}
	mapstate["hp"] = int(m["myhp"].replace(".", ""))
	if CONFIG()["mappe"]["auto"]:
		if CONFIG()["mappe"]["friends"]["flee"] and mapstate["opponents"]["left"] > CONFIG()["mappe"]["friends"]["limit"] \
				and mapstate["enemy"]["name"] in LOOP.state["friends"]:
			@create_task(f"Scappa da {mapstate['enemy']['name']}", client=client)
			async def flee(ctx):
				await ctx.client.send_message(LOOTBOT, "🏳️ Scappa")
			return LOOP.add_task(flee, prio=True)
		text = "🗡 Attacco"
		if LOOP.state["map"]["enemy"]["hp"] >= CONFIG()["mappe"]["soglie"]["hp-rottame"]:
			kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
			for btn in kb:
				if "Riprenditi" in btn: # Was stunned
					text = btn
					break
				match = ROTTAME_BOTTONE_CHECK.match(btn)
				if match: # Can throw a Rottame
					if int(match["n"]) > 0:
						text = btn
					break
		@create_task(f"Attacca avversario mappa : {text}", client=client, text=text)
		async def attack_opponent(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.text)
		LOOP.add_task(attack_opponent, prio=True)


MULTI_ROTTAME_CHECK = re.compile(r"e (?P<n>[0-9]+) 🔩!")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Attacchi l'avversario e gli infliggi.*definitivamente con un colpo mortale!|" +
			r"L'avversario scappa dallo scontro!.*definitivamente con un colpo mortale!|" +
			r"L'avversario ha perso troppi turni!\nHai vinto lo scontro!",
	flags=re.DOTALL
), group=P.map)
async def killed_someone(client, message):
	LOOP.state["map"]["just-killed"] = True
	if ROTTAME_CHECK.search(message.text):
		if LOOP.state["map"]["rottami"] == {}:
			LOOP.state["map"]["rottami"] = 0
		LOOP.state["map"]["rottami"] += message.text.count("🔩 Rottame")
	if MULTI_ROTTAME_CHECK.search(message.text):
		LOOP.state["map"]["rottami"] += int(MULTI_ROTTAME_CHECK.search(message.text)["n"])
	if CASH_CHECK.search(message.text):
		if LOOP.state["map"]["cash"] == {}:
			LOOP.state["map"]["cash"] = 0
		LOOP.state["map"]["cash"] += int(CASH_CHECK.search(message.text)["n"].replace(".", ""))
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("Ucciso Nemico", client=client)(torna_mappa), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"L'avversario scappa dallo scontro!"), group=P.map)
async def enemy_fled(client, message):
	if CONFIG()["mappe"]["auto"]:
		LOOP.add_task(create_task("L'avversario e` fuggito", client=client)(torna_mappa), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Equipaggiamento attuale:\n" +
			r"(?P<weapon>.*)\n" +
			r"(?P<armor>.*)\n" +
			r"(?P<shield>.*)\n" +
			r"💰 (?P<cash>[0-9\.]+)\n" +
			r"🔩 (?P<rottami>[0-9]+)"
), group=P.map)
async def show_sacca(client, message):
	match = message.matches[0]
	LOOP.state["map"]["rottami"] = int(match["rottami"])
	LOOP.state["map"]["cash"] = int(match["cash"].replace(".", ""))
	LOOP.state["map"]["inventory"] = [ match["weapon"], match["armor"], match["shield"] ]

"""
LOCATIONS
"""

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Raggiungi un Emporio, qui puoi acquistare oggetti che ti potranno essere utili.|" +
			r"Raggiungi un 🔁 Centro Scambi, qui puoi scambiare oggetti che ti potranno essere utili.|" +
			r"Raggiungi una 💊 Farmacia, qui puoi recuperare la salute ad un costo onesto.|" +
			r"Raggiungi un 💨 luogo che emana una luce accecante, entri per scoprire i suoi segreti."
), group=P.map)
async def got_to_emporio(client, message):
	b = LOOP.state["map"]["board"]
	pl = LOOP.state["map"]["player"]
	if message.text.startswith("Raggiungi un Emporio"):
		b[pl[0]][pl[1]] = "💸"
	elif message.text.startswith("Raggiungi un 🔁 Centro Scambi"):
		b[pl[0]][pl[1]] = "🔁"
	elif message.text.startswith("Raggiungi una 💊 Farmacia"):
		b[pl[0]][pl[1]] = "💊"
	elif message.text.startswith("Raggiungi un 💨 luogo"):
		b[pl[0]][pl[1]] = "💨"
	if CONFIG()["mappe"]["auto"]:
		@create_task("Accedi all'emporio", client=client)
		async def open_emporio(ctx):
			await ctx.client.send_message(LOOTBOT, "Accedi all'edificio")
		LOOP.add_task(open_emporio, prio=True)

# Emporio
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Puoi acquistare (?P<name>.*) \((?P<stats>.*)\) per (?P<price>[0-9\.]+) §, " +
			r"al momento possiedi (?P<curr>[0-9\.]+) §, procedi\?"
), group=P.map)
async def buy_from_emporio(client, message):
	mapstate = LOOP.state["map"]
	match = message.matches[0]
	mapstate["cash"] = int(match["curr"].replace(".", ""))
	price = int(match["price"].replace(".", ""))
	# TODO check what I'm buying
	if CONFIG()["mappe"]["auto"]:
		if mapstate["cash"] > price:
			@create_task("Compra dall'emporio (mappe)", client=client)
			async def buy_item(ctx):
				await si(ctx)
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(buy_item, prio=True)
			mapstate["cash"] -= price
		else:
			@create_task("Non comprare dall'emporio (mappe)", client=client)
			async def dont_buy_item(ctx):
				await no(ctx)
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(dont_buy_item, prio=True)

# Centro Scambi
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Puoi scambiare (?P<price>[0-9]+) 🔩 Rottami per (?P<name>.*) " +
			r"\((?P<stats>.*)\), al momento ne possiedi (?P<curr>[0-9]+), procedi\?"
), group=P.map)
async def buy_from_centro_scambi(client, message):
	mapstate = LOOP.state["map"]
	match = message.matches[0]
	mapstate["rottami"] = int(match["curr"])
	price = int(match["price"])
	# TODO check what I'm buying
	if CONFIG()["mappe"]["auto"]:
		if mapstate["rottami"] - price >= CONFIG()["mappe"]["soglie"]["rottami"]:
			@create_task("Compra dal centro scambi (mappe)", client=client)
			async def buy_rottami(ctx):
				await si(ctx)
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(buy_rottami, prio=True)
			mapstate["rottami"] -= price
		else:
			@create_task("Non comprare dal centro scambi (mappe)", client=client)
			async def dont_buy_rottami(ctx):
				await no(ctx)
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(dont_buy_rottami, prio=True)

# Farmacia
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Puoi recuperare (?:il (?P<amount>[0-9]+)% di|tutta la) salute " +
			r"al costo di (?P<price>[0-9\.]+) §, al momento possiedi (?P<curr>[0-9\.]+) §, procedi\?"
), group=P.map)
async def buy_from_farmacia(client, message):
	mapstate = LOOP.state["map"]
	match = message.matches[0]
	mapstate["cash"] = int(match["curr"].replace(".", ""))
	price = int(match["price"].replace(".", ""))
	# TODO check what I'm buying
	if CONFIG()["mappe"]["auto"]:
		if mapstate["hp"] < CONFIG()["mappe"]["soglie"]["hp-heal"] and mapstate["cash"] > price:
			@create_task("Curati in Farmacia (mappe)", client=client)
			async def heal(ctx):
				await si(ctx)
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(heal, prio=True)
			mapstate["cash"] -= price
		else:
			@create_task("Non curarti in Farmacia (mappe)", client=client)
			async def dont_heal(ctx):
				await no(ctx)
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(dont_heal, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"(?:Non necessiti di cure|Non hai monete per le cure), procedi?"), group=P.map)
async def no_heal_needed(client, message):
	if CONFIG()["mappe"]["auto"]:
		@create_task("Non necessito di cure", client=client)
		async def no_heal_needed(ctx):
			await si(ctx)
			await random_wait()
			await torna_mappa(ctx)
		LOOP.add_task(no_heal_needed, prio=True)

# Teletrasporto
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"In questo luogo puoi scegliere se utilizzare il teletrasporto, rischiando di ritrovarti in un luogo pericoloso"
), group=P.map)
async def maybe_use_teleport(client, message):
	if CONFIG()["mappe"]["auto"]:
		if CONFIG()["mappe"]["teleport"]:
			@create_task("Usa il teletrasporto", client=client)
			async def ignore_tp(ctx):
				await ctx.client.send_message(LOOTBOT, "Affronta un nemico")
				ctx.state["map"]["controlla"] = True
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(ignore_tp, prio=True)
		else:
			@create_task("Ignora il teletrasporto", client=client)
			async def ignore_tp(ctx):
				await ctx.client.send_message(LOOTBOT, "Esci")
				await random_wait()
				await torna_mappa(ctx)
			LOOP.add_task(ignore_tp, prio=True)
