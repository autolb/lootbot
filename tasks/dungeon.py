import re
import random

from pyrogram import filters

from alemibot import alemiBot

from ..common import LOOTBOT, MAPMATCHERBOT, random_wait, CONFIG, Priorities as P
from ..tasks import si, no, mnu
from ..loop import LOOP, create_task

from .craft import craft_sync, craft_quick

PRIORITY_DEFAULT = [
	"-", "Persona in Pericolo", "Stanza dell'Energia", "Fontana di Mana", "Stanza Vuota",
	"Stanza del Cuore e dello Spirito","Stanza impolverata", "Scrigno", "Meditazione", "Stanza Divisa in Due",
	"Monete", "Spada o Bottino", "Pulsantiera", "Mostro", "Marinaio e Dado",
	"Alchimista dell'Ovest", "Mercante Draconico", "Gioielliere Pazzo", "Predone", "Viandante",
	"Negozio di figurine", "Due Porte", "Vecchina", "Tre Incisioni", "Anziano Saggio",
	"Desideri", "Specchio Magico", "Pozzo Ricco", "Brucaliffo",
	"Trappola", "Ascia Gigante", "Leve", "Crepaccio", "Dragone del Soldato", "Bombarolo",
	"Stanza Esplosiva", "Fessura del Muro", "Mappatore Distratto", "Maledizione Unna", "Vicolo cieco"
]

PRIORITY_RUSH = [
	"Stanza del Cuore e dello Spirito", "Meditazione", "Spada o Bottino", "Persona in Pericolo",
	"Stanza Vuota", "Stanza impolverata", "-", "Mercante Draconico", "Fontana di Mana", "Monete",
	"Scrigno", "Vecchina", " Due Porte", "Alchimista dell'Ovest", "Gioielliere Pazzo",
	"Stanza dell'Energia", "Predone", "Viandante", "Marinaio e Dado", "Anziano Saggio", "Desideri",
	"Specchio Magico", "Negozio di figurine", "Brucaliffo", "Pozzo Ricco", "Crepaccio",
	"Dragone del Soldato", "Bombarolo", "Stanza Esplosiva", "Maledizione Unna", "Fessura del Muro",
	"Stanza Divisa in Due", "Mostro", "Leve", "Tre Incisioni", "Trappola", "Pulsantiera",
	"Ascia Gigante", "Mappatore Distratto", "Vicolo cieco"
]

DIREZIONI = ["⬅️", "⬆️", "➡️"]

# requires client
async def dungeon(ctx):
	ctx.state["dungeon"]["running"] = True
	await ctx.client.send_message(LOOTBOT, "Dungeon 🛡")

# requires client
async def prosegui_dungeon(ctx):
	await ctx.client.send_message(LOOTBOT, "Prosegui il dungeon")

"""
Dungeon start events
"""
# Full heal, Dungeon Rush
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai ricaricato tutta la salute"), group=P.dung)
async def random_heal(client, message): # Cura, aggiorna vita e se in Dungeon Rush, riprendi
	LOOP.state["me"]["hp"] = LOOP.state["me"]["maxhp"]
	if LOOP.state["me"]["rinascita"] == "✨" and LOOP.state["lvl"] and LOOP.state["lvl"] < 50:
		return
	if CONFIG()["dungeon"]["auto"] and LOOP.state["dungeon"]["rush"] and not LOOP.state["dungeon"]["running"]:
		LOOP.add_task(create_task("Avvia Dungeon (Rush)", client=client)(dungeon))

# Cooldown
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"I dungeon sono di nuovo disponibili"), group=P.dung)
async def dungeon_fuori_cooldown(client, message):
	LOOP.state["dungeon"]["cooldown"] = False
	if LOOP.state["me"]["rinascita"] == "✨" and LOOP.state["lvl"] and LOOP.state["lvl"] < 50:
		return
	if CONFIG()["dungeon"]["start"] and not LOOP.state["dungeon"]["running"] \
	and (LOOP.state["dungeon"]["cariche"] == {} or LOOP.state["dungeon"]["cariche"] >= CONFIG()["dungeon"]["cariche"]):
		LOOP.add_task(create_task("Avvia Dungeon", client=client)(dungeon))

# Max cariche
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"L'Energia Esplorativa è carica al massimo"), group=P.dung)
async def energia_al_massimo(client, message):
	LOOP.state["dungeon"]["cariche"] = LOOP.state["dungeon"]["maxcariche"]
	if LOOP.state["me"]["rinascita"] == "✨" and LOOP.state["lvl"] and LOOP.state["lvl"] < 50:
		return
	if not LOOP.state["dungeon"]["running"] and not LOOP.state["dungeon"]["cooldown"] and CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Avvia Dungeon", client=client)(dungeon))

# Main Menu
CARICHE_CHECK = re.compile(r"🔋 (?P<curr>[0-9]+)\/(?P<max>[0-9]+)")
DUNGEON_RUNNING = re.compile(r"❗️ Esplora il dungeon \((?:Stanza (?P<room>[0-9]+)\/(?P<tot>[0-9]+)|Boss)\) (?:[🕐💥 ]+) (?P<time>.*) 🔋 (?P<charges>[0-9]+|∞)\/(?P<maxc>[0-9]+)")
DUNGEON_RESTART = re.compile(r"Entra in un dungeon")
DUNGEON_COOLDOWN_CHECK = re.compile(r"Attesa dungeon fino alle")
@alemiBot.on_message(filters.chat(LOOTBOT) &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=P.dung) # Resume doing dungeons after anything else: dungeons take a while!
async def main_menu_triggers(client, message): # TODO maybe move main menu tasks in their respective task files?
	LOOP.state["dungeon"]["running"] = False
	match = CARICHE_CHECK.search(message.text)
	if match:
		LOOP.state["dungeon"]["cariche"] = int(match["curr"])
		LOOP.state["dungeon"]["maxcariche"] = int(match["max"])
	match = DUNGEON_RUNNING.search(message.text)
	if match:
		dung = LOOP.state["dungeon"]
		dung["cooldown"] = False
		if match["charges"] == "∞":
			dung["cariche"] = 60
			dung["rush"] = True
		else:
			dung["cariche"] = int(match["charges"])
			dung["rush"] = False
		if match["room"]:
			dung["stanza"] = int(match["room"])
			dung["totali"] = int(match["tot"])
		dung["tempo"] = match["time"]
		if dung["wait-cariche"] == {}:
			dung["wait-cariche"] = 0
		if len(LOOP) < 1 and CONFIG()["dungeon"]["auto"] \
			and ((not dung["rush"] and dung["cariche"] >= CONFIG()["dungeon"]["cariche"] and dung["cariche"] >= dung["wait-cariche"])
				or (dung["rush"] and LOOP.state["me"]["hp"] > LOOP.state["me"]["maxhp"] * CONFIG()["dungeon"]["hp"])) :
			dung["wait-cariche"] = 0
			LOOP.add_task(create_task("Check + continue dungeon", client=client)(dungeon))
	elif DUNGEON_COOLDOWN_CHECK.search(message.text):
		if len(LOOP) < 1 and CONFIG()["dungeon"]["start"] and (CONFIG()["dungeon"]["varco"] or "Avanti nel tempo" in LOOP.state["imprese"]["todo"]) \
		and (LOOP.state["dungeon"]["varchi"] == {} or LOOP.state["dungeon"]["varchi"] > 0) \
		and (LOOP.state["dungeon"]["usi-varchi"] == {} or LOOP.state["dungeon"]["usi-varchi"] > 0):
			LOOP.add_task(create_task("Check + varco dungeon", client=client)(dungeon))
			LOOP.state["dungeon"]["cooldown"] = False
	elif DUNGEON_RESTART.search(message.text):
		LOOP.state["dungeon"]["cooldown"] = False
		if LOOP.state["me"]["rinascita"] == "✨" and LOOP.state["me"]["lvl"] and LOOP.state["me"]["lvl"] < 50:
			return
		if len(LOOP) < 1 and CONFIG()["dungeon"]["start"]:
			LOOP.add_task(create_task("Check + restart dungeon", client=client)(dungeon))

# Prova a usare sempre un varco se in cooldown se auto-varco on, al peggio torni poi al menu
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Puoi tornare nei dungeon alle .*!"), group=P.dung)
async def dungeon_in_cooldown(client, message):
	LOOP.state["dungeon"]["cooldown"] = True
	if CONFIG()["dungeon"]["start"]:
		if CONFIG()["dungeon"]["varco"] or "Avanti nel tempo" in LOOP.state["imprese"]["todo"]:
			@create_task("Prova a usare Varco Temporale", client=client)
			async def try_use_varco(ctx):
				await ctx.client.send_message(LOOTBOT, "Usa Varco Temporale")
			LOOP.add_task(try_use_varco, prio=True)
		else:
			LOOP.add_task(create_task("Dungeon in cooldown, menu", client=client)(mnu))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Puoi tornare nei dungeon alle .*Ne possiedi (?P<owned>[0-9]+)(?:, puoi utilizzarli ancora (?P<uses>[0-9]+) volte|)",
	flags=re.DOTALL
), group=P.dung)
async def usa_varco_temporale(client, message):
	if CONFIG()["dungeon"]["start"]:
		m = message.matches[0].groupdict()
		LOOP.state["dungeon"]["varchi"] = int(m["owned"])
		LOOP.state["dungeon"]["usi-varchi"] = 3
		if "uses" in m and m["uses"] is not None and m["uses"] != "":
			LOOP.state["dungeon"]["usi-varchi"] = int(m["uses"])
		if (CONFIG()["dungeon"]["varco"] or "Avanti nel tempo" in LOOP.state["imprese"]["todo"]) \
		and LOOP.state["dungeon"]["varchi"] > 0 \
		and LOOP.state["dungeon"]["usi-varchi"] > 0:
			@create_task("Usa Varco Temporale", client=client)
			async def use_varco(ctx):
				await si(ctx)
				await random_wait()
				await mnu(ctx)
				ctx.state["dungeon"]["varchi"] -=1
			LOOP.add_task(use_varco, prio=True)
		else:
			LOOP.add_task(create_task("Non usare Varco Temporale", client=client)(mnu))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Mappatura team per l'istanza"), group=P.dung)
async def messaggio_mappatura(client, message):
	if CONFIG()["dungeon"]["mapmatcher"]:
		await message.forward(MAPMATCHERBOT)

"""
Cariche esplorative
"""
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai ottenuto (?P<n>[0-9]+) Cariche Esplorative"), group=P.dung)
async def cariche_a_caso(client, message):
	dung = LOOP.state["dungeon"]
	if dung["cariche"] == {}:
		dung["cariche"] = 0
	if dung["wait-cariche"] == {}:
		dung["wait-cariche"] = 0
	dung["cariche"] += int(message.matches[0]["n"])
	if CONFIG()["dungeon"]["auto"] and not dung["cooldown"] and not dung["running"] \
	and dung["cariche"] >= CONFIG()["dungeon"]["cariche"] and dung["cariche"] >= dung["wait-cariche"]:
		dung["wait-cariche"] = 0
		LOOP.add_task(create_task("Riprendi Dungeon", client=client)(dungeon))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non hai abbastanza energia per"), group=P.dung)
async def basta_dungeon(client, message): # Finita la carica per proseguire il dungeon
	LOOP.state["dungeon"]["wait-cariche"] = 10
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Interrompi Dungeon", client=client)(mnu))

"""
Sta venendo avviato un nuovo dungeon, scegli o il primo o di generarne un'altro
"""
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Benvenut. nella Sala di Ritrovo degli Esploratori"), group=P.dung)
async def sala_ritrovo_esploratori(client, message):
	if CONFIG()["dungeon"]["start"]:
		@create_task("Avvia nuovo Dungeon", client=client, title=message.reply_markup.keyboard[1][0]) # TODO don't auto choose 1st choice
		async def start_dungeon(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.title)
		LOOP.add_task(start_dungeon, prio=True)


@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Seleziona una variante di dungeon esistente o creane una nuova"), group=P.dung)
async def scegli_istanza_dungeon(client, message):
	if CONFIG()["dungeon"]["start"]:
		kb = message.reply_markup.keyboard
		choice = kb[0][0] if kb[1][0] == "Torna al dungeon" else kb[1][0] # if 2nd btn is "Torna al Dungeon", no instances exist! Choose 2nd button (last dungeon started) otherwise
		if CONFIG()["dungeon"]["maledetto"]:
			kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
			for btn in kb:
				if "🧨" in btn:
					choice = btn
					break
		@create_task("Avvia un nuovo dungeon", client=client, choice=choice)
		async def choose_dungeon_variant(ctx):
			await ctx.client.send_message(LOOTBOT, choice)
			await random_wait()
			await si(ctx)
			ctx.state["dungeon"]["once"] = False
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(choose_dungeon_variant, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Il dungeon è stato creato"), group=P.dung)
async def dungeon_creato_entraci(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Entra nel dungeon", client=client)
		async def entra_nel_dungeon(ctx):
			await ctx.client.send_message(LOOTBOT, "Entra nel dungeon")
		LOOP.add_task(entra_nel_dungeon, prio=True)

"""
Main loop del dungeon
"""
MAPPATURA = re.compile(r"🗺 Mappatura (?:\(team\)|)\n(?P<left>.*) \| (?P<up>.*) \| (?P<right>.*)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"(?:🛡 |.) (?P<room>[0-9]+)\/(?P<tot>[0-9]+)\n(?:⏱ |.) (?P<time>.*)\n(?:🔋|.) (?P<charge>[0-9]+|∞)\/(?P<maxchrg>[0-9]+)\n(?:❤️|🧡|🖤)(?: |)(?P<hp>[0-9\.]+) hp"
), group=P.dung)
async def dungeon_main_screen(client, message):
	# Parse state from Dungeon main screen
	match = message.matches[0]
	dung = LOOP.state["dungeon"]
	dung["stanza"] = int(match["room"])
	dung["totali"] = int(match["tot"])
	if match["charge"] == "∞": # Dungeon Rush!
		dung["rush"] = True
		dung["cariche"] = 60
	else:
		dung["rush"] = False
		dung["cariche"] = int(match["charge"])
	dung["tempo"] = match["time"]
	LOOP.state["me"]["hp"] = match["hp"]
	if CONFIG()["dungeon"]["auto"] and dung["interrupt"]:
		dung["interrupt"] = False
		return LOOP.add_task(create_task("Sospendi il dungeon", client=client)(mnu), prio=True)
	if "Che pigrizia" in LOOP.state["imprese"]["todo"]:
		@create_task("Abbandona dungeon", client=client)
		async def scappa_dal_dungeon(ctx):
			await ctx.client.send_message(LOOTBOT, "Scappa")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Non usare")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Si")
			await random_wait()
			await mnu(ctx)
		return LOOP.add_task(scappa_dal_dungeon, prio=True)
	if CONFIG()["dungeon"]["mapmatcher"] and dung["stanza"] == dung["totali"] and not dung["once"]:
		@create_task("Inoltra mappatura dungeon", client=client)
		async def forward_dungeon_mapping(ctx):
			ctx.state["dungeon"]["once"] = True
			await ctx.client.send_message(LOOTBOT, "/mappatura")
			await random_wait()
			await mnu(ctx)
		return LOOP.add_task(forward_dungeon_mapping, prio=True)
	if CONFIG()["dungeon"]["auto"] and dung["cariche"] < dung["wait-cariche"]:
		return LOOP.add_task(create_task("Aspetta abbastanza cariche", client=client)(mnu), prio=True)
	if CONFIG()["dungeon"]["auto"] and message.reply_markup \
	and message.reply_markup.keyboard[0][0] == "Prosegui":
		@create_task(f"Ritorna ad evento dungeon", client=client)
		async def dung_forth(ctx):
			await ctx.client.send_message(LOOTBOT, "Prosegui")
		return LOOP.add_task(dung_forth, prio=True)
	if dung["cariche"] < 10 and CONFIG()["dungeon"]["auto"]:
		return LOOP.add_task(create_task("Interrompi Dungeon", client=client)(mnu), prio=True)

	# Pathfinding
	m = MAPPATURA.search(message.text)
	choice = -1
	ways = ["-", "-", "-"]
	priorities = PRIORITY_RUSH if dung["rush"] else PRIORITY_DEFAULT
	if CONFIG()["dungeon"]["mob-prio"]:
		priorities = ["Mostro"] + priorities
	if CONFIG()["imprese"]["auto"]:
		if "Mente acuta" in LOOP.state["imprese"]["todo"]:
			priorities = ["Stanza del Cuore e dello Spirito", "Meditazione"] + priorities
		if "Un prezioso scambio" in LOOP.state["imprese"]["todo"]:
			priorities = ["Fessura del Muro", "Gioielliere Pazzo"] + priorities
		if "Assetato" in LOOP.state["imprese"]["todo"]:
			priorities = ["Vecchina", "Alchimista dell'Ovest"] + priorities
		if "Toc toc" in LOOP.state["imprese"]["todo"]:
			priorities = ["Anziano Saggio"] + priorities
		if "Io non me ne vado" in LOOP.state["imprese"]["todo"]:
			priorities = ["Brucaliffo"] + priorities
		if "Sarà per la prossima" in LOOP.state["imprese"]["todo"]:
			priorities = ["Leve"] + priorities
		if "Fissato con le pulizie" in LOOP.state["imprese"]["todo"]:
			priorities = ["Stanza impolverata", "Specchio Magico"] + priorities
		if "Scambio draconico" in LOOP.state["imprese"]["todo"]:
			priorities = ["Mappatore Distratto", "Mercante Draconico"] + priorities
		if "Cercatore di tesori" in LOOP.state["imprese"]["todo"]:
			priorities = ["Monete", "Desideri", "Spada o Bottino"] + priorities
		if "Potrebbe essere utile" in LOOP.state["imprese"]["todo"]:
			priorities = ["Stanza impolverata"] + priorities
		if "Ci vorrebbe un bel quadro" in LOOP.state["imprese"]["todo"]:
			priorities = ["Stanza Divisa in Due", "Stanza Vuota"] + priorities
	if m:
		ways = [ m["left"], m["up"], m["right"] ]
		for i in range(len(ways)): # strip monster level, kinda jank but should fix
			if ways[i].startswith("Mostro"):
				ways[i] = "Mostro"
		LOOP.state["dungeon"]["ways"] = ways
		for way in priorities:
			if way in ways:
				choice = ways.index(way)
				break
	if choice < 0:
		choice = random.randint(0, 2)
	LOOP.state["dungeon"]["choice"] = ways[choice]
	if CONFIG()["dungeon"]["auto"]:
		@create_task(f"Dungeon : go \'{ways[choice]}\'", client=client, direction=DIREZIONI[choice])
		async def dung_choice(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.direction)
		LOOP.add_task(dung_choice, prio=True)

"""
FIGHT
"""
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non disponi di pozioni per recuperare salute"), group=P.dung)
async def no_more_pozze(client, message):
	if CONFIG()["dungeon"]["auto"]:
		CONFIG()["dungeon"]["auto"] = False # Changing player config is bad but this is a quite extreme case
		await message.pin()
		LOOP.add_task(create_task("Finite le pozioni, spegni dungeon!", client=client)(mnu))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r".*(Stai combattendo contro un mostro!|Incontri un(?:a|o|) (?P<name>.*) di livello (?P<lvl>[0-9]+)|" +
	r"Hai colpito il mostro e hai inferto|Non hai inflitto danno al mostro|Il mostro ha evitato il tuo colpo!|Non sei riuscito a colpire il mostro)")
, group=P.dung)
async def attaccalo(client, message): # Vai al combattimento
	args = message.matches[0].groupdict()
	if "name" in args and args["name"]:
		LOOP.state["fight"]["name"] = args["name"]
	if "lvl" in args and args["lvl"]:
		LOOP.state["fight"]["lvl"] = int(args["lvl"])
	if CONFIG()["dungeon"]["auto"]:
		if LOOP.state["interrupt"]:
			LOOP.add_task(create_task("Sospendi il combattimento (dungeon)", client=client)(mnu), prio=True)
		else:
			@create_task(f"Attacca {LOOP.state['fight']['name']} ({LOOP.state['fight']['lvl']})", client=client)
			async def start_fight(ctx):
				await ctx.client.send_message(LOOTBOT, "Attacca")
			LOOP.add_task(start_fight, prio=True)

def cast_for_impresa():
	return CONFIG()["imprese"]["auto"] and (
		"Mago da strapazzo" in LOOP.state["imprese"]["todo"] or
		"Sprecone di mana" in LOOP.state["imprese"]["todo"] or
		"Fuoco e fiamme" in LOOP.state["imprese"]["todo"] or
		"Inondazione" in LOOP.state["imprese"]["todo"] or
		"Sparafulmini" in LOOP.state["imprese"]["todo"] or
		"Crittatore" in LOOP.state["imprese"]["todo"] or
		LOOP.state["imprese"]["naked"])

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"(?P<name>.*)\n\n(?:❤️|.) (?P<enhp>[0-9\.]+) hp\n(?P<enstate>.*)\n\n" +
			r"(?P<weapons>.*)\n\n(?:❤️|.) (?P<myhp>[0-9\.]+) hp(?: (?:🤍|🖤|.) " +
			r"(?P<mylif>[0-9]+)\/(?P<mymaxlif>[0-9]+)|)\n(?P<mystate>.*)",
	flags=re.DOTALL
), group=P.dung)
async def dentro_al_fight(client, message): # Schermata principale
	m = message.matches[0]
	fight = {
		"name" : m["name"],
		"hp" : int(m["enhp"].replace(".", "")),
		"lvl" : LOOP.state["fight"]["lvl"], # Use this again!
		"state" : m["enstate"],
		"weapon" : m["weapons"].split("\n"),
		"interventi" : int(m["mylif"])
	}
	LOOP.state["me"]["hp"] = int(m["myhp"].replace(".", ""))
	LOOP.state["me"]["state"] = m["mystate"]
	LOOP.state["fight"] = fight

	hp_thr = CONFIG()["dungeon"]["hp"] * LOOP.state["me"]["maxhp"]
	hp_spell_thr = CONFIG()["dungeon"]["spell"]["hp"] * LOOP.state["me"]["maxhp"]
	if CONFIG()["imprese"]["auto"] and CONFIG()["imprese"]["activity"] \
	and "Ancora qui sei?!" in LOOP.state["imprese"]["todo"]:
		hp_thr = 0.2 * LOOP.state["me"]["maxhp"]
	if CONFIG()["dungeon"]["auto"]:
		if LOOP.state["me"]["hp"] < hp_thr:
			if LOOP.state["dungeon"]["rush"]:
				LOOP.add_task(create_task("Ferma dungeon (rush) per salute bassa", client=client)(mnu), prio=True)
			else:
				@create_task("Ripristina Salute", client=client)
				async def heal(ctx):
					await ctx.client.send_message(LOOTBOT, "❣️")
					await random_wait()
					await ctx.client.send_message(LOOTBOT, "Torna al dungeon")
				LOOP.add_task(heal, prio=True)
		else:
			if not LOOP.state["dungeon"]["casting"] and not LOOP.state["cast"]["stop"] and (
					(CONFIG()["dungeon"]["spell"]["auto"] and LOOP.state["me"]["hp"] <= hp_spell_thr)
					or cast_for_impresa()
			):
				@create_task("Lancia Incantesimo", client=client)
				async def cast(ctx):
					await ctx.client.send_message(LOOTBOT, "Incantesimi ✨")
				LOOP.add_task(cast, prio=True)
			else:
				LOOP.state["dungeon"]["casting"] = False
				action = "Attacca {fight['name']}"
				if message.reply_markup:
					action = message.reply_markup.keyboard[0][0]
				else:
					action = f"Attacca {LOOP.state['fight']['name']}"
				@create_task(f"Attacca {fight['name']}", client=client, attack=action)
				async def attack(ctx):
					await ctx.client.send_message(LOOTBOT, ctx.attack)
				LOOP.add_task(attack, prio=True)

NO_SPELLS = re.compile(r"Non possiedi alcun incantesimo, puoi ottenerli attraverso la Sintesi!")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"^Incantesimi:"), group=P.dung)
async def scegli_incantesimo(client, message):
	if CONFIG()["dungeon"]["auto"] and (CONFIG()["dungeon"]["spell"]["auto"] or cast_for_impresa()):
		rateo = CONFIG()["dungeon"]["spell"]["rateo"]
		if "Inondazione" in LOOP.state["imprese"]["todo"]:
			rateo = [20, 15, 15]
		elif "Sparafulmini" in LOOP.state["imprese"]["todo"]:
			rateo = [15, 20, 15]
		elif "Fuoco e fiamme" in LOOP.state["imprese"]["todo"]:
			rateo = [15, 15, 20]
		elif "Crittatore" in LOOP.state["imprese"]["todo"]:
			rateo = [17, 17, 17]
		rateo_str = ",".join(str(el) for el in rateo)
		if NO_SPELLS.search(message.text) and not LOOP.state["cast"]["stop"]:
			@create_task("Sintetizza Incantesimo", client=client, text=rateo_str)
			async def create_spell(ctx):
				await ctx.client.send_message(LOOTBOT, f"/sintesi {ctx.text}")
			LOOP.add_task(create_spell, prio=True)
		else:
			@create_task("Lancia Incantesimo", client=client, spell=message.reply_markup.keyboard[0][0])
			async def cast_spell(ctx):
				ctx.state["dungeon"]["casting"] = True
				await ctx.client.send_message(LOOTBOT, ctx.spell)
			LOOP.add_task(cast_spell, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non hai abbastanza mana di quel tipo"), group=P.dung)
async def non_abbastanza_mana(client, message):
	LOOP.state["cast"]["stop"] = True

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Iniziare la sintesi utilizzando le unità selezionate?"), group=P.dung)
async def sicuro_della_sintesi(client, message):
	LOOP.state["cast"]["stop"] = False
	if CONFIG()["dungeon"]["auto"] and (CONFIG()["dungeon"]["spell"]["auto"] or cast_for_impresa()):
		LOOP.add_task(create_task("Conferma Sintesi", client=client)(si), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai sintetizzato"), group=P.dung)
async def sintesi_completata(client, message):
	LOOP.state["cast"]["stop"] = False
	if CONFIG()["dungeon"]["auto"] and (CONFIG()["dungeon"]["spell"]["auto"] or cast_for_impresa()):
		@create_task("Sintesi Completata", client=client)
		async def finished_synth(ctx):
			await ctx.client.send_message(LOOTBOT, "Torna al dungeon")
		LOOP.add_task(finished_synth, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Sei arrivato alla stanza finale"), group=P.dung)
async def dungeon_completato(client, message):
	LOOP.state["dungeon"]["boss"] = True

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai ucciso il mostro"), group=P.dung)
async def vinto_fight(client, message): # Ucciso il mostro
	if CONFIG()["dungeon"]["auto"]:
		if LOOP.state["dungeon"]["boss"]:
			LOOP.add_task(create_task("Dungeon terminato", client=client)(mnu))
			LOOP.state["dungeon"]["cooldown"] = True
		else:
			LOOP.add_task(create_task("Prosegui il dungeon", client=client)(prosegui_dungeon), prio=True)
	LOOP.state["dungeon"]["boss"] = False

"""
Dead
"""
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non puoi entrare nel dungeon da esausto"), group=P.dung)
async def sono_morto_pd(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Torna in Vita", client=client)
		async def ress(ctx):
			await ctx.client.send_message(LOOTBOT, "Torna in Vita")
		LOOP.add_task(ress, prio=True)
	if CONFIG()["log"]["pin"]["death"]:
		await message.pin()

BTN_CHECK = re.compile(r"Intervento Divino \((?P<n>[0-9])\)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Vuoi usare una Piuma di Fenice, una Cenere di Fenice"), group=P.dung)
async def come_resuscitare(client, message):
	if CONFIG()["dungeon"]["auto"]:
		kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
		for btn in kb:
			match = BTN_CHECK.match(btn)
			if match:
				if int(match["n"]) > 0:
					@create_task("Usa Intervento Divino", client=client, msg=btn)
					async def use_divine_intervention(ctx):
						await ctx.client.send_message(LOOTBOT, ctx.msg)
						await random_wait()
						await mnu(ctx)
					LOOP.add_task(use_divine_intervention, prio=True)
				break
		
"""
Below are dungeon events with their triggers
"""
# Stanza Vuota
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Entri in una stanza apparentemente vuota, cosa fai?"), group=P.dung)
async def stanza_vuota(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Stanza vuota, prosegui", client=client)
		async def prosegui(ctx):
			await ctx.client.send_message(LOOTBOT, "...")
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(prosegui, prio=True)

# Vicolo Cieco
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r".*Questo è un vicolo cieco.*", flags=re.DOTALL), group=P.dung)
async def devi_tornare_indietro(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Vicolo cieco (dungeon)", client=client)
		async def vicolo_cieco(ctx):
			await ctx.client.send_message(LOOTBOT, "Torna indietro")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Prosegui il dungeon")
		LOOP.add_task(vicolo_cieco, prio=True)

# Persona in Pericolo
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r".*uomo ferito e sanguinante|una donna impaurita|angolo una ragazza|un anziano dolorante|un bambino che piange.*",
	flags=re.DOTALL)
, group=P.dung)
async def persona_in_pericolo(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Aiuta persona (dungeon)", client=client)
		async def aiuta_persona(ctx):
			await ctx.client.send_message(LOOTBOT, "Aiuta")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Prosegui il dungeon")
		LOOP.add_task(aiuta_persona, prio=True)

# Ninfa
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r".*Una ragazza seduta su una roccia vicino ad una sorgente*",
	flags=re.DOTALL)
, group=P.dung)
async def ragazza_seduta(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Avvicina ragazza (dungeon)", client=client)
		async def avvicina_ragazza(ctx):
			await ctx.client.send_message(LOOTBOT, "Ti avvicini alla ragazza")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Prosegui il dungeon")
		LOOP.add_task(avvicina_ragazza, prio=True)

# Crepaccio | ?Marinaio e Dado | ??? | ??? | Stanza Esplosiva | Dragone del Soldato | Bombarolo
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Entri in una stanza che anziché una parete ha un'immenso crepaccio|" +
			r".*(propone una partita ai dadi|oggetti a buon prezzo|un uomo magro con un cappello|una stanza piena di esplosivi|immenso drago di LastSoldier95).*|" +
			r"Sull'angolo della stanza noti un uomo magro con un cappello a forma di Bomba",
	flags=re.DOTALL
), group=P.dung)
async def ignora_e_prosegui(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Ignora stanza (dungeon)", client=client)
		async def ignora_stanza(ctx):
			await ctx.client.send_message(LOOTBOT, "Ignora")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Prosegui il dungeon")
		LOOP.add_task(ignora_stanza, prio=True)

# Loot ?????
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r".*vedi un mucchietto di monete|Nella stanza sembra esserci uno scrigno.*",
	flags=re.DOTALL
), group=P.dung)
async def prendi_il_loot(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Prendi loot (dungeon)", client=client)
		async def get_dat_loot(ctx):
			await ctx.client.send_message(LOOTBOT, "Prendi")
		LOOP.add_task(get_dat_loot, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Hai trovato uno Scrigno! Ma appena lo tocchi"
), group=P.dung)
async def bad_loot(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Mostro, attacca (dungeon)", client=client)
		async def no_loot_only_monster(ctx):
			await ctx.client.send_message(LOOTBOT, "Attacca")
		LOOP.add_task(no_loot_only_monster, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Hai trovato [0-9]+x|Aprendo uno strano scrigno hai trovato|Corri verso il mucchietto"
), group=P.dung)
async def good_loot(client, message):
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Era effettivamente loot (dungeon)",
						client=client)(prosegui_dungeon), prio=True)

# Fontana di Mana
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Appena entrato nella stanza noti subito una strana fontana situata nel centro"
), group=P.dung)
async def fontana_mana(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Fontana di Mana (dungeon)", client=client)
		async def get_dat_mana(ctx):
			await ctx.client.send_message(LOOTBOT, "Esamina")
		LOOP.add_task(get_dat_mana, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Ti avvicini alla fontana e vedi che l'acqua"
), group=P.dung)
async def fontana_good(client, message):
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Ricevuto mana, prosegui dungeon",
									client=client)(prosegui_dungeon), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Ti avvicini alla fontana per esaminarla meglio"
), group=P.dung)
async def fontana_fight(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Mostro nella fontana, attacca (dungeon)", client=client)
		async def no_loot_only_monster(ctx):
			await ctx.client.send_message(LOOTBOT, "Attacca")
		LOOP.add_task(no_loot_only_monster, prio=True)

# Pozzo monete
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Una luce esagerata ti avvolge"), group=P.dung)
async def posso_di_monete(client, message):
	# non provare a pescare che perdi cash
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Versa nel pozzo", client=client, text=message.reply_markup.keyboard[0][0])
		async def paga_pozzo(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.text)
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(paga_pozzo, prio=True)

# Stanza piena di Polvere
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Entri in una stanza completamente piena di polvere"), group=P.dung)
async def stanza_di_polvere(client, message):
	if CONFIG()["dungeon"]["auto"]:
		if CONFIG()["dungeon"]["polvere"] or LOOP.state["dungeon"]["rush"] \
		or (CONFIG()["imprese"]["auto"] and "Fissato con le pulizie" in LOOP.state["imprese"]["todo"]):
			@create_task("Raccogli polvere (dungeon)", client=client)
			async def raccogli_polvere_stanza(ctx):
				await ctx.client.send_message(LOOTBOT, "Raccogli")
			LOOP.add_task(raccogli_polvere_stanza, prio=True)
		else:
			@create_task("Ignora stanza polvere (dungeon)", client=client)
			async def ignora_polvere(ctx):
				await ctx.client.send_message(LOOTBOT, "Ignora")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(ignora_polvere, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Inizi a spolverare, consumi"), group=P.dung)
async def spolverata_stanza(client, message):
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Spolverato", client=client)(prosegui_dungeon), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non hai abbastanza Cariche Esplorative per spolverare, te ne servono (?P<n>[0-9]+)!"), group=P.dung)
async def non_abbastanza_cariche_per_spolverare(client, message):
	LOOP.state["dungeon"]["wait-cariche"] = int(message.matches[0]["n"])
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Aspetta cariche per spolverare", client=client)(mnu), prio=True)

# Porta Misteriosa
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Oltrepassando la porta ti trovi davanti ad altre due porte, una con un'aria familiare"), group=P.dung)
async def stanza_porta_misteriosa(client, message):
	if CONFIG()["dungeon"]["auto"]:
		porta = "Misteriosa"
		if LOOP.state["dungeon"]["stanza"] > (LOOP.state["dungeon"]["totali"] // 2):
			porta = "Normale"
		@create_task(f"Scegli porta {porta}", client=client, porta=porta)
		async def scegli_porta(ctx):
			await ctx.client.send_message(LOOTBOT, f"Porta {ctx.porta}")
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(scegli_porta, prio=True)

# Ey amico sai chi sono
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r".*Si presenta così un tipo strano in un angolino della stanza"), group=P.dung)
async def ey_amico_sai_chi_sono(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Ey amico sai chi sono", client=client)
		async def disturba(ctx):
			await ctx.client.send_message(LOOTBOT, "Disturba")
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(disturba, prio=True)

# Potentissima Energia Magica
GOD_ITEM = re.compile("(?i).* di (?:Xocotl|Hydros|Hoenir|Phoenix|Loki|Odino|Thor|Efesto|Zeus|Poseidone)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Spalancata la porta della stanza vieni sbalzato all'indietro da una potentissima energia magica"
), group=P.dung)
async def potentissima_energia_magica(client, message):
	if CONFIG()["dungeon"]["auto"]:
		choice = "Passi di fianco"
		if not LOOP.state["dungeon"]["rush"] and LOOP.state["me"]["equip"] and \
		(GOD_ITEM.search(LOOP.state["me"]["equip"]["armor"]) or GOD_ITEM.search(LOOP.state["me"]["equip"]["shield"])):
		   choice = "Passi attraverso"
		@create_task(f"Energia Magica : {choice}", client=client, choice=choice)
		async def energia_magica(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.choice)
			await random_wait()
			if ctx.choice == "Passi Attraverso":
				pass #maybe extra shit to do???
			await prosegui_dungeon(ctx)
		LOOP.add_task(energia_magica, prio=True)

# Tre Incisioni
STANZA_CHECK = re.compile(r"(?P<n>[0-9])\. Stanza (?P<dest>[0-9]+) \((?P<dir>.*)\): (?P<name>.*)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"In questa stanza non noti nessuna porta, al loro posto 3 incisioni con un pulsante ciascuna"
), group=P.dung)
async def stanza_tre_incisioni(client, message):
	kb = message.reply_markup.keyboard
	tasti = []
	for row in kb: # This is just 5 buttons in the end but will work for any number
		for el in row:
			if el != "Cambia Incisione" and el != "Torna al menu":
				tasti.append(el)
	LOOP.state["dungeon"]["incisioni"]["attuali"] = tasti

	if not CONFIG()["dungeon"]["auto"]:
		return

	curr = LOOP.state["dungeon"]["stanza"]
	choice = None
	furthest = curr
	for t in tasti:
		m = STANZA_CHECK.search(t)
		if not m:
			continue
		if m["name"] == "Mostro" and int(m["dest"]) > curr:
			choice = t
			break
		if CONFIG()["dungeon"]["incisioni"] and int(m["dest"]) > furthest \
		and t not in LOOP.state["dungeon"]["incisioni"]["sbagliate"]:
			choice = t
			furthest = int(m["dest"])
	
	if choice is None:
		if LOOP.state["dungeon"]["cariche"] >= 10:
			@create_task("Cambia incisioni", client=client)
			async def cambia_incisioni(ctx):
				await ctx.client.send_message(LOOTBOT, "Cambia Incisione")
				await random_wait()
				await si(ctx)
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(cambia_incisioni, prio=True)
		else:
			LOOP.add_task(create_task(
				"Cariche insufficienti per cambiare", client=client)(mnu), prio=True)
	else:
		LOOP.state["dungeon"]["incisioni"]["scelta"] = choice
		@create_task(f"Prova incisioni +{furthest}", client=client, choice=choice)
		async def prova_incisione(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.choice)
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(prova_incisione, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Premi un pulsante ma sul muro appare un messaggio con scritto"), group=P.dung)
async def incisione_sbagliata(client, message): # Incisione sbagliata!
	if LOOP.state["dungeon"]["incisioni"]["sbagliate"] == {}:
		LOOP.state["dungeon"]["incisioni"]["sbagliate"] = []
	LOOP.state["dungeon"]["incisioni"]["sbagliate"].append(LOOP.state["dungeon"]["incisioni"]["scelta"])

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Premi un pulsante e sul muro appare un messaggio con scritto"), group=P.dung)
async def incisione_giusta(client, message): # Incisione corretta!
	LOOP.state["dungeon"]["incisioni"]["sbagliate"] = []

# Spada Conficcata
ACCUMULO_CHECK = re.compile(r"Fin ora hai accumulato (?P<acc>[0-9\.]+) § per la probabilità del (?P<n>[0-9]+)% di rischiare la vita")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Entri in una stanza piena d'oro luccicante e una spada"), group=P.dung)
async def spada_conficcata(client, message):
	if CONFIG()["dungeon"]["auto"]:
		m = ACCUMULO_CHECK.search(message.text)
		if CONFIG()["dungeon"]["kit"]["farm"] and m and int(m["n"]) < CONFIG()["dungeon"]["kit"]["limit"]:
			@create_task("Accumula monete (dungeon)", client=client)
			async def accumula_monete(ctx):
				await ctx.client.send_message(LOOTBOT, "Accumula monete")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(accumula_monete, prio=True)
		else:
			@create_task("Estrai Spada", client=client)
			async def estrai_spada(ctx):
				await ctx.client.send_message(LOOTBOT, "Estrai spada")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(estrai_spada, prio=True)

# Stanza Bottoni Ghiacciati
HP_CHECK = re.compile(r"(?:❤️|.) (?P<hp>[0-9\.]+) hp")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Appena aperta la porta della stanza, un freddo polare ti avvolge"), group=P.dung)
async def stanza_bottoni_ghiacciati(client, message):
	if CONFIG()["dungeon"]["auto"]:
		LOOP.state["me"]["hp"] = int(HP_CHECK.search(message.text)["hp"].replace("." , ""))
		if LOOP.state["me"]["hp"] < (CONFIG()["dungeon"]["hp"] * LOOP.state["me"]["maxhp"]):
			if LOOP.state["dungeon"]["rush"]:
				LOOP.add_task(create_task("Ferma dungeon (rush) per salute bassa", client=client)(mnu), prio=True)
			else:
				@create_task("Ripristina Salute", client=client)
				async def heal(ctx):
					await ctx.client.send_message(LOOTBOT, "❣️")
					await random_wait()
					await ctx.client.send_message(LOOTBOT, "Torna al dungeon")
				LOOP.add_task(heal, prio=True)
		else:
			choice = 2
			if CONFIG()["dungeon"]["try-buttons"]:
				if LOOP.state["dungeon"]["pulsanti-provati"] == {} \
				or set(LOOP.state["dungeon"]["pulsanti-provati"]) == set([1, 2, 3, 4, 5, 6]): # safety
					LOOP.state["dungeon"]["pulsanti-provati"] = []
				choice = random.choice(list(set([ 1, 2, 3, 4, 5, 6 ]) - set(LOOP.state["dungeon"]["pulsanti-provati"])))
				LOOP.state["dungeon"]["pulsanti-provati"].append(choice)
			@create_task("Prova pulsante ghiacciato (dungeon)", client=client, choice=choice)
			async def prova_pulsante(ctx):
				await ctx.client.send_message(LOOTBOT, str(ctx.choice))
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(prova_pulsante, prio=True)
			
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai trovato il pulsante corretto! Prosegui alla prossima stanza"), group=P.dung)
async def bottone_corretto(client, message):
	LOOP.state["dungeon"]["pulsanti-provati"] = []

# Stanza del cuore e dello Spirito
CONCENTRAZIONI_CHECK = re.compile(r"Fin ora ti sei concentrato (?P<n>[0-9]) volte")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Raggiungi una stanza completamente trasparente, sembra quasi fluttuare nel cielo"), group=P.dung)
async def stanza_del_cuore_e_dello_spirito(client, message):
	if CONFIG()["dungeon"]["auto"]:
		conc = 0
		m = CONCENTRAZIONI_CHECK.search(message.text)
		if m:
			conc = int(m["n"])
		if (LOOP.state["dungeon"]["rush"] and conc < 7) or conc < CONFIG()["dungeon"]["concentrazioni"] or (CONFIG()["imprese"]["auto"] 
				and "Mente acuta" in LOOP.state["imprese"]["todo"] and conc < 1):
			@create_task("Concentrati (dungeon)", client=client)
			async def concentrate(ctx):
				await ctx.client.send_message(LOOTBOT, "Concentrati")
			LOOP.add_task(concentrate, prio=True)
		else:
			@create_task("Termina Concentrazione (dungeon)", client=client)
			async def stop_concentration(ctx):
				await ctx.client.send_message(LOOTBOT, "Termina Concentrazione")
			LOOP.add_task(stop_concentration, prio=True)

# Stanza della meditazione profonda
MEDITAZIONI_CHECK = re.compile(r"Fin ora hai meditato (?P<n>[0-9]) volte")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Raggiungi una stanza con un'incisione profonda: Stanza della Meditazione"), group=P.dung)
async def stanza_della_meditazione(client, message):
	if CONFIG()["dungeon"]["auto"]:
		med = 0
		m = MEDITAZIONI_CHECK.search(message.text)
		if m:
			med = int(m["n"])
		if (LOOP.state["dungeon"]["rush"] and med < 7) or med < CONFIG()["dungeon"]["meditazioni"] or (CONFIG()["imprese"]["auto"]
				and "Mente acuta" in LOOP.state["imprese"]["todo"] and med < 1):
			@create_task("Medita (dungeon)", client=client)
			async def medita(ctx):
				await ctx.client.send_message(LOOTBOT, "Medita")
			LOOP.add_task(medita, prio=True)
		else:
			@create_task("Non meditare (dungeon)", client=client)
			async def stop_meditation(ctx):
				await ctx.client.send_message(LOOTBOT, "Termina Meditazione")
			LOOP.add_task(stop_meditation, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Ti sei concentrato|Per la concentrazione prolungata|Ti senti talmente pronto da non necessitare|" +
			r"Inizi una profonda meditazione|Per la meditazione prolungata|Affamato d’azione, decidi di non perdere tempo"
), group=P.dung)
async def concentrato_o_meditato(client, message):
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Meditato/Concentrato, prosegui", client=client)(prosegui_dungeon), prio=True)

# Non abbastanza cariche, torna al menu
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non hai abbastanza Cariche Esplorative, ne servono (?P<n>[0-9]+)"), group=P.dung)
async def troppe_poche_cariche(client, message):
	LOOP.state["dungeon"]["wait-cariche"] = int(message.matches[0]["n"])
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Mancano Cariche Esplorative per meditare/concentrare!", client=client)(mnu), prio=True)
   
"""
STANZE CON DAILIES
"""
# Brucaliffo
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Tra una fitta coltre di fumo grigio appare un maestoso brucaliffo"), group=P.dung)
async def regala_al_brucaliffo_per_daily(client, message):
	if CONFIG()["dungeon"]["auto"]:
		if CONFIG()["imprese"]["auto"] and "Io non me ne vado" in LOOP.state["imprese"]["todo"] \
		and not LOOP.state["dungeon"]["brucaliffo-no-item"]:
			@create_task("Accetta scambio Brucaliffo", client=client)
			async def regala_al_brucaliffo(ctx):
				await ctx.client.send_message(LOOTBOT, "Offri...")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, CONFIG()["dungeon"]["item"])
				await random_wait()
				await si(ctx) # This is extra if it fails! I should add a dedicated handler and listen if the gift was made
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(regala_al_brucaliffo, prio=True)
		else:
			@create_task("Ignora Brucaliffo", client=client)
			async def ignora_stanza(ctx):
				await ctx.client.send_message(LOOTBOT, "Ignora")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Prosegui il dungeon")
			LOOP.add_task(ignora_stanza, prio=True)
			LOOP.state["dungeon"]["brucaliffo-no-item"] = False

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non possiedi l'oggetto selezionato"), group=P.dung)
async def cannot_do_brucaliffo(client, message):
	LOOP.state["dungeon"]["brucaliffo-no-item"] = True

# Gioielliere Pazzo
ITEM_SEARCH = re.compile(r"in cambio di un particolare oggetto, in questo caso: (?P<item>[^✅☑️]+)(?: (?P<state>✅|☑️)|), accetti")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Entri in una stanza completamente luccicante, quasi accecante" # Gioielliere
), group=P.dung)
async def acquista_dal_gioielliere_daily(client, message):
	if CONFIG()["dungeon"]["auto"]:
		if CONFIG()["imprese"]["auto"] and "Un prezioso scambio" in LOOP.state["imprese"]["todo"]:
			match = ITEM_SEARCH.search(message.text)
			if match["state"] == "✅":
				@create_task("Accetta vendita gioielliere", client=client)
				async def accept_trade_jeweler(ctx):
					await si(ctx)
					await random_wait()
					await prosegui_dungeon(ctx)
				LOOP.add_task(accept_trade_jeweler, prio=True)
				LOOP.state["craft"]["attempt"]["gioielliere"] = False
			elif not LOOP.state["craft"]["attempt"]["gioielliere"]:
				LOOP.state["craft"]["attempt"]["gioielliere"] = True # if this fails, don't try again
				if match["state"] == "☑️":
					LOOP.add_task(create_task(f"Crea {match['item']} (1 step) per gioielliere",
									client=client, item=match["item"])(craft_quick))
				else:
					LOOP.add_task(create_task(f"Crea {match['item']} per gioielliere",
									 client=client, recipe=match["item"])(craft_sync))
			elif not CONFIG()["imprese"]["wait-failed"]:
				@create_task("Ignora Gioielliere (daily ma can't craft)", client=client)
				async def ignore_merch(ctx):
					await ctx.client.send_message(LOOTBOT, "No")
					await random_wait()
					await prosegui_dungeon(ctx)
				LOOP.add_task(ignore_merch, prio=True)
		else:
			@create_task("Evita Gioielliere (no daily)", client=client)
			async def ignore_merch(ctx):
				await ctx.client.send_message(LOOTBOT, "No")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(ignore_merch, prio=True)

# Alchimista dell'Ovest
OGGETTO_ALCHIMISTA = re.compile(r"scambieresti il tuo (?P<item>[^✅☑️]+)(?: (?P<state>✅|☑️|)|) per (?P<trade>.*)?")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Non fai che un passo, una voce mite ma ferma ti paralizza"
), group=P.dung)
async def alchimista_dell_ovest_daily(client, message):
	if CONFIG()["dungeon"]["auto"]:
		if CONFIG()["imprese"]["auto"] and "Assetato" in LOOP.state["imprese"]["todo"]:
			match = OGGETTO_ALCHIMISTA.search(message.text)
			if match["state"] == "✅":
				@create_task("Accetta offerta Alchimista", client=client)
				async def accept_alch(ctx):
					await si(ctx)
					await random_wait()
					await prosegui_dungeon(ctx)
				LOOP.add_task(accept_alch, prio=True)
				LOOP.state["craft"]["attempt"]["alchimista"] = False
			elif not LOOP.state["craft"]["attempt"]["alchimista"]:
				LOOP.state["craft"]["attempt"]["alchimista"] = True # if this fails, don't try again
				if match["state"] == "☑️":
					LOOP.add_task(create_task(f"Crea {match['item']} (1 step) per alchimista",
									client=client, item=match["item"])(craft_quick))
				else:
					LOOP.add_task(create_task(f"Crea {match['item']} per alchimista",
									 client=client, recipe=match["item"])(craft_sync))
			elif not CONFIG()["imprese"]["wait-failed"]:
				@create_task("Ignora alchimista (can't craft)", client=client)
				async def ignore_alch(ctx):
					await ctx.client.send_message(LOOTBOT, "No")
					await random_wait()
					await prosegui_dungeon(ctx)
				LOOP.add_task(ignore_alch, prio=True)
		else:
			@create_task("Ignora alchimista (no daily)", client=client)
			async def ignore_alch(ctx):
				await ctx.client.send_message(LOOTBOT, "No")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(ignore_alch, prio=True)

# Vecchina
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Aprendo la porta ti ritrovi in un ambiente aperto, con alberi e liane"), group=P.dung)
async def stanza_con_vecchia_signora(client, message):
	if CONFIG()["dungeon"]["auto"]:
		if CONFIG()["imprese"]["auto"] and "Assetato" in LOOP.state["imprese"]["todo"]:
			@create_task("Segui Vecchina (daily)", client=client)
			async def ignore_merch(ctx):
				await ctx.client.send_message(LOOTBOT, "Segui la Vecchia")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(ignore_merch, prio=True)
		else:
			@create_task("Evita Vecchina (no daily)", client=client)
			async def ignore_merch(ctx):
				await ctx.client.send_message(LOOTBOT, "Ignora")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(ignore_merch, prio=True)

# Mercante Draconico
OGGETTO_DRACONICO = re.compile(r"fornisce oggetti utili al proprio drago in cambio di (?P<qty>[0-9]+)x (?P<name>.*)(?: (?P<state>✅|)|)\.")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Entri in una stanza che non ha affatto le sembianze di una stanza, piuttosto un grosso parco" # Mercante Draconico
), group=P.dung)
async def acquista_draconico_se_daily(client, message):
	if CONFIG()["dungeon"]["auto"]:
		match = OGGETTO_DRACONICO.search(message.text)
		if CONFIG()["imprese"]["auto"] and "Scambio draconico" in LOOP.state["imprese"]["todo"] \
		and match and match["state"] == "✅":
			@create_task("Accetta offerta Mercante Draconico", client=client)
			async def accept_drac(ctx):
				await si(ctx)
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(accept_drac, prio=True)
		else:
			@create_task("Ignora Mercante Draconico", client=client)
			async def no_merc_drac(ctx):
				await no(ctx)
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(no_merc_drac, prio=True)

# Specchio
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Entri in una stanza con un piccolo specchio al centro. Ti avvicini"), group=P.dung)
async def stanza_con_specchio_magico(client, message):
	if CONFIG()["dungeon"]["auto"]:
		if CONFIG()["imprese"]["auto"] and "Fissato con le pulizie" in LOOP.state["imprese"]["todo"]:
			@create_task("Tocca lo specchio (daily)", client=client)
			async def ignore_merch(ctx):
				await ctx.client.send_message(LOOTBOT, "Tocchi lo specchio")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(ignore_merch, prio=True)
		else:
			@create_task("Evita Specchio (no daily)", client=client)
			async def ignore_merch(ctx):
				await ctx.client.send_message(LOOTBOT, "Ignora")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(ignore_merch, prio=True)

# Predone del deserto, Mercante di Figurine
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Nella stanza incontri un predone del deserto dall'aria docile|" +   # Predone del deserto
			r"Entri in un negozio stranamente elegante, con migliaia di Figurine" # Mercante di Figurine
), group=P.dung)
async def interagisci_solo_se_daily(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Ignora interazione (no daily)", client=client)
		async def ignore_interaction(ctx):
			await ctx.client.send_message(LOOTBOT, "Ignora")
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(ignore_interaction, prio=True)

# Vecchio con occhi sbarrati
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Al centro della stanza vedi un signore anziano con gli occhi sbarrati"
), group=P.dung)
async def vecchio_occhi_sbarrati(client, message):
	if CONFIG()["dungeon"]["auto"]:
		kb = message.reply_markup.keyboard
		if CONFIG()["imprese"]["auto"] and "Toc toc" in LOOP.state["imprese"]["todo"]:
			@create_task("Accetta trade chiavi", client=client, txt=kb[0][0])
			async def dai_daily_vecchio(ctx):
				await ctx.client.send_message(LOOTBOT, ctx.txt)
				await random_wait()
				await si(ctx) # TODO make this in 2 or 3 steps and check for key availability
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(dai_daily_vecchio, prio=True)
		else:
			@create_task("Ignora trade chiavi", client=client)
			async def vecchio_occhi_sbarrati(ctx):
				await ctx.client.send_message(LOOTBOT, "Ignora")
				await random_wait()
				await prosegui_dungeon(ctx)
			LOOP.add_task(vecchio_occhi_sbarrati, prio=True)

# ???
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Davanti a te si erge un portale completamente rosso, una voce rimbomba"), group=P.dung)
async def portale_completamente_rosso(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("ESSERE RICCO SFONDATO!!!11!11!", client=client)
		async def essere_ricco_sfondato(ctx):
			await ctx.client.send_message(LOOTBOT, "Essere ricco sfondato")
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(essere_ricco_sfondato, prio=True)

# Stanza divisa in due
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Raggiungi una stanza suddivisa in due"), group=P.dung)
async def stanza_divisa_in_due(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Stanza divisa, oggetto raro", client=client)
		async def stanza_divisa(ctx):
			await ctx.client.send_message(LOOTBOT, "Più Raro")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Attacca")
		LOOP.add_task(stanza_divisa, prio=True)

# Fessura nel muro
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Questa stanza è strana, scorgi solamente una fessura sul muro"), group=P.dung)
async def stanza_con_fessura(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Inserisci monete nella fessura (dungeon)", client=client)
		async def inserisci(ctx):
			await ctx.client.send_message(LOOTBOT, "Inserisci Monete")
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(inserisci, prio=True)

# Stanza con le leve
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Il corridoio si stringe in un'umida strettoia, sembrerebbe un vicolo cieco!"), group=P.dung)
async def stanza_con_le_leve(client, message):
	if CONFIG()["dungeon"]["auto"]:
		choice = random.choice([ "Sinistra", "Centro", "Destra" ])
		@create_task(f"Stanza con 3 leve : {choice}", client=client, choice=choice)
		async def lever_room(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.choice)
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(lever_room, prio=True)

# Ascia Gigante
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Un cartello con un punto esclamativo ti preoccupa, al centro della stanza c'è un taglio"), group=P.dung)
async def stanza_ascia_gigante(client, message):
	if CONFIG()["dungeon"]["auto"]:
		@create_task("Ascia gigante (dungeon)", client=client)
		async def ascia(ctx):
			await ctx.client.send_message(LOOTBOT, "Procedi")
			await random_wait()
			await prosegui_dungeon(ctx)
		LOOP.add_task(ascia, prio=True)

# Maledizione Unna
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Entrando nella stanza pesti una leva nascosta, la maledizione Unna t'ha colpito"), group=P.dung)
async def maledizione_unna(client, message):
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Maledizione Unna! (dungeon)", client=client)(prosegui_dungeon))

# Trappola
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Percorrendo un corridoio scivoli su una pozzanghera giallognola|" +
			r"Camminando per raggiungere la prossima stanza|" +
			r"Uno strano pulsante rosso come un pomodoro ti incuriosisce|" +
			r"Vedi un Nano della terra di Grumpi|" +
			r"Hai schivato con destrezza una trappola piazzata" # Unica positiva 
), group=P.dung)
async def trappola(client, message):
	if CONFIG()["dungeon"]["auto"]:
		LOOP.add_task(create_task("Trappola (dungeon)", client=client)(prosegui_dungeon))
