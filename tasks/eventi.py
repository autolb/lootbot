import re
from datetime import datetime, timedelta

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, CONFIG, random_wait, Priorities as P
from plugins.lootbot.tasks import mnu, si
from plugins.lootbot.loop import LOOP, create_task

# Requires client
async def dust_gen(ctx):
	await ctx.client.send_message(LOOTBOT, "⏲	Generatore di Polvere (Evento) ♨️")

# Requires client
async def itinerario(ctx):
	await ctx.client.send_message(LOOTBOT, "🏹Itinerario Propizio (Evento) 🎯")

# Requires client

"""
Main Menu
"""

CURRENT_ITINERARIO_CHECK = re.compile(r"🗾 Itinerario fino")
CURRENT_MISSION_CHECK = re.compile(r"Missione fino")
CURRENT_CAVA_CHECK = re.compile(r"🗻 Esplorazione cava fino")
ESTRAZIONE_CHECK = re.compile(r"⛏ Estrazione di Mana (?:Rosso|Giallo|Blu) in corso")
GENERAZIONE_CHECK = re.compile(r"⏲ Generatore acceso \((?P<curr>[0-9]+)\/(?P<max>[0-9]+) unità\)")
ATTESA_ISPEZIONE = re.compile(r"🔦 Gnomo in (?:esplorazione|ispezione) fino alle (?P<time>[0-9:]+)")
@alemiBot.on_message(filters.chat(LOOTBOT) &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=P.event)
async def main_menu_starters(client, message):
	kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
	if len(LOOP) < 1 and CONFIG()["eventi"]["miniera"]["auto"] and "⛏ Miniere di Mana (Evento) ⛰ " in kb:
		if not ESTRAZIONE_CHECK.search(message.text) and not CURRENT_CAVA_CHECK.search(message.text):
			@create_task("Apri miniera", client=client)
			async def go_to_mana_mine(ctx):
				await ctx.client.send_message(LOOTBOT, "⛏ Miniere di Mana (Evento) ⛰")
			LOOP.add_task(go_to_mana_mine)
	if len(LOOP) < 1 and CONFIG()["eventi"]["generatore"]["auto"] and "⏲ Generatore di Polvere (Evento) ♨️" in kb:
		if LOOP.state["generatore"]["last"] == {}:
			LOOP.state["generatore"]["last"] = datetime.now()
		match = GENERAZIONE_CHECK.search(message.text)
		if match:
			amount = int(match["curr"])
			maxstorage = int(match["max"])
			curr_delta = datetime.now() - LOOP.state["generatore"]["last"]
			if amount == maxstorage or (amount >= CONFIG()["eventi"]["generatore"]["min"] and
					curr_delta.total_seconds() % 3600 < CONFIG()["eventi"]["generatore"]["maxt"]):
				LOOP.add_task(create_task("Avvia Generatore", client=client)(dust_gen))
		else:
			LOOP.add_task(create_task("Avvia Generatore", client=client)(dust_gen))
	if len(LOOP) < 1 and "💰Il Ricercato (Evento) 👺" in kb \
	and CONFIG()["eventi"]["ricercato"]["auto"] and not ATTESA_ISPEZIONE.search(message.text):
		LOOP.add_task(create_task("Avvia caccia al Ricercato", client=client)(ricercato))
	if len(LOOP) < 1 and "🏹Itinerario Propizio (Evento) 🎯" in kb and not LOOP.state["itinerario"]["non-disponibile"] \
	and CONFIG()["eventi"]["itinerario"]["auto"] and not CURRENT_MISSION_CHECK.search(message.text) \
												and not CURRENT_ITINERARIO_CHECK.search(message.text):
		LOOP.add_task(create_task("Not doing any itinerario?", client=client)(itinerario))

"""
Ricercato
"""
RICERCATO_NAME = re.compile(r"👺 (?:Il|La) ricercat. è (?P<name>[^ ]+) con abilità ")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Il tuo status da ricercato:"), group=P.event)
async def start_wanted_hunt(client, message):
	if CONFIG()["eventi"]["ricercato"]["auto"] and not LOOP.state["ispezione"]["ongoing"]:
		@create_task("Avvia caccia al ricercato", client=client, player=RICERCATO_NAME.search(message.text)["name"])
		async def start_manhunt(ctx):
			await ctx.client.send_message(LOOTBOT, f"Ispeziona {ctx.player}")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Invia Piedelesto")
			await random_wait()
			await si(ctx)
			ctx.state["ispezione"]["ongoing"] = True
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(start_manhunt, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Il tuo gnomo ha catturato il ricercato e hai ottenuto la sua taglia|" +
			r"Il tuo tentativo di cattura è stato un FALLIMENTO"
))
async def manhunt_finished(client, message):
	LOOP.state["ispezione"]["ongoing"] = False
	if CONFIG()["eventi"]["ricercato"]["auto"]:
		LOOP.add_task(create_task("Riavvia caccia al Ricercato", client=client)(ricercato))

"""
Itinerario
"""
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"^Itinerario Propizio"), group=P.event)
async def choose_itinerario_region(client, message):
	if CONFIG()["eventi"]["itinerario"]["auto"]:
		@create_task("Scegli Regione itinerario", client=client)
		async def choose_region(ctx):
			await ctx.client.send_message(LOOTBOT, "Regione Anomala (S)")
		LOOP.add_task(choose_region, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Seleziona la zona in cui iniziare un itinerario"), group=P.event)
async def choose_itinerario_zone(client, message):
	if CONFIG()["eventi"]["itinerario"]["auto"]:
		kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
		for btn in kb:
			if CONFIG()["eventi"]["itinerario"]["zone"] in btn:
				@create_task("Scegli Zona itinerario", client=client, zone=btn)
				async def choose_zone(ctx):
					await ctx.client.send_message(LOOTBOT, ctx.zone)
				LOOP.add_task(choose_zone, prio=True)
				break

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Iniziare l'itinerario nel(?:la|) (?P<dove>.+)?"), group=P.event)
async def avvia_itinerario(client, message):
	if CONFIG()["eventi"]["itinerario"]["auto"]:
		@create_task("Avvia itinerario", client=client)
		async def start_itinerario(ctx):
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(start_itinerario, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Itinerario completato! Hai ottenuto"), group=P.event)
async def terminato_itinerario(client, message):
	if CONFIG()["eventi"]["itinerario"]["auto"]:
		LOOP.state["interrupt"] = True
		if len(LOOP) < 1:
			LOOP.add_task(create_task("Itinerario completato, torna al menu", client=client)(mnu))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Oggi l'evento non è disponibile, torna nel weekend"), group=P.event)
async def itinerario_non_disponibile_pd_edo(client, message):
	LOOP.state["itinerario"]["non-disponibile"] = True
	if CONFIG()["eventi"]["itinerario"]["auto"]:
		LOOP.add_task(create_task("Itinerario non disponibile", client=client)(mnu), prio=True)

"""
MINIERA
"""

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Le miniere sono state chiuse, hai ricevuto"), group=P.event)
async def miniere_chiuse(client, message):
	if CONFIG()["log"]["pin"]["reward"]:
		await message.pin()
		
MANA_TIPI = { "blu" : "Miniera Trek", "giallo" : "Miniera Valke", "rosso" : "Miniera Inche" }
MANA_CHECK = re.compile(r"Miniera (?:Trek|Valke|Inche) \((?:🌊 Blu|⚡️ Giallo|🔥 Rosso) (?P<n>[0-9]+)\/ora")
OWNED_MANA = re.compile(r"Al momento possiedi:\n🌊 Blu: (?P<blu>[0-9\.]+)\n⚡️ Giallo: (?P<giallo>[0-9\.]+)\n🔥 Rosso: (?P<rosso>[0-9\.]+)\nAvrai possibilità di estrarre")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Seleziona la miniera dalla quale iniziare a estrarre mana"), group=P.event)
async def choose_mine(client, message): # TODO make this slimmer
	if not CONFIG()["eventi"]["miniera"]["auto"]:
		return
	text = ""
	kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
	if CONFIG()["eventi"]["miniera"]["lower"]:
		curr = OWNED_MANA.search(message.text)
		minmana = 999999999999999 # kek
		best = "blu"
		for mana in ["blu", "giallo", "rosso"]:
			if int(curr[mana].replace(".", "")) < minmana:
				minmana = int(curr[mana].replace(".", ""))
				best = mana
		for btn in kb:
			if btn.startswith(MANA_TIPI[best]):
				text = btn
				break
	else:
		best = 0
		for btn in kb:
			match = MANA_CHECK.match(btn)
			if match and int(match["n"]) > best:
				best = int(match["n"])
				text = btn
	@create_task("Scegli miniera", client=client, btn=text)
	async def choose_mine(ctx):
		await ctx.client.send_message(LOOTBOT, ctx.btn)
		await random_wait()
		await si(ctx)
	LOOP.add_task(choose_mine, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Estrazione iniziata, torna qui tra qualche ora"), group=P.event)
async def started_mine_correctly(client, message):
	if CONFIG()["eventi"]["miniera"]["auto"]:
		LOOP.add_task(create_task("Avviata miniera, torna al menu", client=client)(mnu), prio=True)

"""
GENERATORE
"""
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Il generatore è pieno! Svuotalo per produrre"), group=P.event)
async def generatore_pieno(client, message):
	if CONFIG()["eventi"]["generatore"]["auto"]:
		LOOP.add_task(create_task("Generatore pieno!", client=client)(dust_gen))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Gestione Generatore"), group=P.event)
async def aziona_generatore(client, message):
	if CONFIG()["eventi"]["generatore"]["auto"]:
		@create_task("Aziona Generatore", client=client)
		async def activate_dust_gen(ctx):
			await ctx.client.send_message(LOOTBOT, "Aziona Generatore")
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(activate_dust_gen, prio=True)

TIME_CHECK = re.compile(r"Ultima attività: (?P<date>[0-9\/]+ alle [0-9\:]+)")
DELTA = timedelta(minutes=30)
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Hai generato fin ora (?P<curr>[0-9]+)\/(?P<max>[0-9]+) unità di polvere, vuoi spegnere"
), group=P.event)
async def get_dust(client, message): # TODO add time based logic!
	if CONFIG()["eventi"]["generatore"]["auto"]:
		amount = int(message.matches[0]["curr"])
		maxstorage = int(message.matches[0]["max"])
		match = TIME_CHECK.search(message.text)
		if match:
			LOOP.state["generatore"]["last"] = datetime.strptime(match["date"], '%d/%m/%Y alle %H:%M:%S')
		else:
			LOOP.state["generatore"]["last"] = datetime.now()
		curr_delta = datetime.now() - LOOP.state["generatore"]["last"]
		if amount == maxstorage or (amount >= CONFIG()["eventi"]["generatore"]["min"] and
				curr_delta.total_seconds() % 3600 < CONFIG()["eventi"]["generatore"]["maxt"]):
			@create_task("Svuota Generatore di Polvere", client=client)
			async def svuota_gen(ctx):
				await ctx.client.send_message(LOOTBOT, "Ritira")
				ctx.state["generatore"]["last"] = datetime.now()
			LOOP.add_task(svuota_gen)
		else:
			LOOP.add_task(create_task("Aspetta per generatore", client=client)(mnu), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai ottenuto (?P<n>[0-9]+)x Polvere!"), group=P.event)
async def ritirata_polvere(client, message):
	if CONFIG()["eventi"]["generatore"]["auto"]:
		LOOP.add_task(create_task("Svuotato generatore, torna al menu", client=client)(mnu), prio=True)
