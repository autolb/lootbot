import re

from collections import Counter

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, random_wait, CONFIG
from plugins.lootbot.tasks import si, mnu, rifugio
from plugins.lootbot.loop import LOOP, create_task

def score(numbers):
	assert len(numbers) == 5
	if numbers[4] == numbers[3]+1 and numbers[3] == numbers[2]+1 \
	and numbers[2] == numbers[1]+1 and numbers[1] == numbers[0]+1: # scala
		return 75 + max(numbers)/100
	c = sorted(Counter(numbers).most_common(),
				key=lambda tup: (tup[1], tup[0]), reverse=True)
	if c[0][1] == 5: # poker ++
		return 120 + c[0][0]
	elif c[0][1] == 4: # poker
		return 105 + c[0][0] + c[1][0]/100
	elif c[0][1] == 3 and c[1][1] == 2: # full
		return 90 + c[0][0] + c[1][0]/100
	elif c[0][1] == 3: # tris
		return 45 + c[0][0] + c[0][1]/100
	elif c[0][1] == 2 and c[1][1] == 2: # doppia coppia
		return 30 + c[0][0] + c[1][0] + c[2][0]/100
	elif c[0][1] == 2: # coppia
		return 15 + c[0][0] + c[1][0]/100
	else:
		return max(numbers)

GNOMO_CHECK = re.compile(r"Gnomo in attesa di istruzioni")
ATTESA_ISPEZIONE = re.compile(r"🔦 Gnomo in (?:esplorazione|ispezione) fino alle (?P<time>[0-9:]+)")
@alemiBot.on_message(filters.chat(LOOTBOT) &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=53)
async def main_menu_triggers(client, message):
	if LOOP.state["ispezione"]["rimaste"] == {}:
		LOOP.state["ispezione"]["rimaste"] = 10
	if ATTESA_ISPEZIONE.search(message.text) or GNOMO_CHECK.search(message.text):
		LOOP.state["ispezione"]["ongoing"] = True
	kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
	if "💰Il Ricercato (Evento) 👺" not in kb and len(LOOP) < 1 and CONFIG()["ispezione"]["auto"]:
		if GNOMO_CHECK.search(message.text):
			@create_task("Contatta lo gnomo (da menu)", client=client)
			async def contatta_lo_gnomo(ctx):
				await ctx.client.send_message(LOOTBOT, "Contatta lo gnomo")
			LOOP.add_task(contatta_lo_gnomo)
		elif LOOP.state["ispezione"]["rimaste"] > 0 and not LOOP.state["ispezione"]["ongoing"]:
			@create_task("Avvia ispezione", client=client)
			async def goto_rifugio(ctx):
				await ctx.client.send_message(LOOTBOT, "Rifugio 🔦")
			LOOP.add_task(goto_rifugio)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"Il tuo gnomo non è riuscito a raggiungere il rifugio nemico, dannazione!|" +
	r"La tua combinazione di rune \((?P<me>[0-9]+)\) è (?:migliore|peggiore) di quella del guardiano \((?P<other>[0-9]+)\)!"
), group=53)
async def riavvia_ispezione(client, message):
	LOOP.state["dungeon"]["interrupt"] = True
	LOOP.state["ispezione"]["ongoing"] = False
	if CONFIG()["ispezione"]["auto"] and LOOP.state["cash"] > 2000:
		LOOP.add_task(create_task("Riavvia Ispezione", client=client)(rifugio))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Ispezione in corso fino alle|Stai svolgendo un ispezione, completala"), group=53)
async def cant_start_ispezione(client, message):
	LOOP.state["ispezione"]["ongoing"] = True
	if CONFIG()["ispezione"]["auto"]:
		LOOP.add_task(create_task("Gia` in ispezione", client=client)(mnu))

ISPEZIONI_LEFT = re.compile(r"Puoi ancora effettuare (?P<number>[0-9]+) ispezioni, subirne")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern="Bentornat. nel tuo 🏕"), group=53)
async def avvia_nuova_ispezione(client, message):
	if CONFIG()["ispezione"]["auto"] and LOOP.state["cash"] > 2000:
		m = ISPEZIONI_LEFT.search(message.text)
		LOOP.state["ispezione"]["rimaste"] = int(m["number"])
		if int(m["number"]) > 0 and not LOOP.state["ispezione"]["ongoing"]:
			@create_task("Avvia nuova ispezione", client=client)
			async def new_inspection(ctx):
				await ctx.client.send_message(LOOTBOT, "Ispezione 🔦")
			LOOP.add_task(new_inspection, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Invia uno gnomo ad un rifugio di un altro giocatore per cercare"), group=53)
async def scegli_verso_chi(client, message):
	if CONFIG()["ispezione"]["auto"]:
		@create_task("Matchmaking", client=client)
		async def ispezione_matchmaking(ctx):
			await ctx.client.send_message(LOOTBOT, "Matchmaking (2.000 §)")
		LOOP.add_task(ispezione_matchmaking, prio=True)

MATCHMAKING = re.compile(r"con abilità (?P<skill>[0-9\.]+)\.\nAlloggia in un (?P<rif>.*) ed il drago (?P<drakename>.*) " +
						 r"\((?P<drakelvl>[0-9]+)\) sorveglia la sua entrata\.")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Stai per inviare uno gnomo servitore al rifugio"), group=53)
async def scegli_gnomo(client, message):
	if CONFIG()["ispezione"]["auto"]:
		match = MATCHMAKING.search(message.text)
		skill = int(match["skill"].replace(".", ""))
		drake = int(match["drakelvl"])
		gnomo = "Occhiofurbo"
		if CONFIG()["imprese"]["auto"]:
			if "Il mio esercito" in LOOP.state["imprese"]["todo"]:
				gnomo = "Piedelesto"
			elif "Ispezione modesta" in LOOP.state["imprese"]["todo"]:
				gnomo = "Testacalda"
		ME = LOOP.state["me"]
		if not CONFIG()["ispezione"]["mm"] or not ME["abilita"] or not ME["dragon"]["lvl"] or (ME["abilita"] >= skill and ME["dragon"]["lvl"] >= drake) \
		or (LOOP.state["ispezione"]["matchmaking"] and LOOP.state["ispezione"]["matchmaking"] > CONFIG()["ispezione"]["reroll"]):
			@create_task(f"Invia {gnomo}", client=client, gnomo=gnomo)
			async def send_occhiofurbo(ctx):
				ctx.state["ispezione"]["matchmaking"] = 0
				await ctx.client.send_message(LOOTBOT, f"Invia {ctx.gnomo}")
				await random_wait()
				await si(ctx)
				ctx.state["ispezione"]["ongoing"] = True
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(send_occhiofurbo, prio=True)
		else:
			if not LOOP.state["ispezione"]["matchmaking"]:
				LOOP.state["ispezione"]["matchmaking"] = 1
			@create_task("Re-matchmaking", client=client)
			async def re_matchmaking(ctx):
				await ctx.client.send_message(LOOTBOT, "Matchmaking (§)")
			LOOP.add_task(re_matchmaking, prio=True)
			LOOP.state["ispezione"]["matchmaking"] += 1
		
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"Il tuo gnomo è arrivato al rifugio nemico, il guardiano del cancello ti propone uno strano gioco con le Rune"
), group=53)
async def ispezione_successo(client, message):
	if CONFIG()["ispezione"]["auto"]:
		@create_task("Avvia gioco delle Rune", client=client)
		async def start_game(ctx):
			await ctx.client.send_message(LOOTBOT, "Contatta lo Gnomo 💭")
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(start_game)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"Il tuo gnomo ha terminato la raccolta delle rune|Il tuo gnomo ha cambiato le rune richieste"
), group=53)
async def game_is_ready(client, message):
	if CONFIG()["ispezione"]["auto"]:
		@create_task("Vai alle Rune", client=client)
		async def goto_game(ctx):
			await ctx.client.send_message(LOOTBOT, "Contatta lo Gnomo")
		LOOP.add_task(goto_game)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"Per entrare nel rifugio di (?P<name>.*) devi possedere delle Rune.*💬 (?P<rune>[0-9 ]+)\n\nPuoi cambiare le Rune ancora (?P<left>[0-9]) volte",
flags=re.DOTALL), group=53)
async def game_event(client, message):
	if not CONFIG()["ispezione"]["auto"]:
		return
	m = message.matches[0]
	attempts = int(m["left"])
	if attempts == 0:
		@create_task("Conferma combinazione", client=client)
		async def confirm_rune(ctx):
			await ctx.client.send_message(LOOTBOT, "Tieni Combinazione")
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(confirm_rune, prio=True)
		return
	LOOP.state["ispezione"]["name"] = m["name"]
	LOOP.state["ispezione"]["rune"] = m["rune"]
	rune = [ int(r) for r in m["rune"].split() ]
	change = []
	val = score(rune)
	if val < CONFIG()["ispezione"]["keep"]:
		count = Counter(rune)
		keep = count.most_common()[0][0]
		for i, r in zip(range(1, len(rune) + 1), rune):
			if r != keep:
				change.append(str(i))
	if len(change) == 0 or (CONFIG()["imprese"]["auto"] and
			"Fortunello" in LOOP.state["imprese"]["todo"]):
		@create_task("Conferma combinazione", client=client)
		async def accept_rune(ctx):
			await ctx.client.send_message(LOOTBOT, "Tieni Combinazione")
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(accept_rune, prio=True)
		return
	out = ",".join(change)
	@create_task("Cambia rune {out}", client=client, text=out)
	async def change_runes(ctx): # TODO split this up!
		await random_wait()
		await ctx.client.send_message(LOOTBOT, "Cambia Rune")
		await random_wait()
		await ctx.client.send_message(LOOTBOT, ctx.text)
		await random_wait()
		await si(ctx)
		await random_wait()
		await mnu(ctx)
	LOOP.add_task(change_runes, prio=True)
	
	
