import asyncio
import re

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, random_wait, CONFIG
from plugins.lootbot.tasks import si, mnu
from plugins.lootbot.loop import LOOP, create_task

def autocava_check():
	return (CONFIG["cava"]["auto"] or (CONFIG["imprese"]["activity"] and
		("Evoluzione draconica" in LOOP.state["imprese"]["todo"]
		or "Quanta fretta" in LOOP.state["imprese"]["todo"]
		or "Minatore costante" in LOOP.state["imprese"]["todo"]
		or "Mucchio di pietre" in LOOP.state["imprese"]["todo"]
		or "Indecisione" in LOOP.state["imprese"]["todo"])))

autocava = filters.create(lambda _, __, ___: autocava_check())

async def esplorazioni(ctx):
	await ctx.client.send_message(LOOTBOT, "Esplorazioni 🧗‍♀")

CURRENT_MISSION_CHECK = re.compile(r"Missione fino")
CURRENT_INCARICO_CHECK = re.compile(r"Incarico in corso fino")
CURRENT_CAVA_CHECK = re.compile(r"Esplorazione cava fino")
ESTRAZIONE_CHECK = re.compile(r"⛏ Estrazione di Mana (?:Rosso|Giallo|Blu) in corso")
@alemiBot.on_message(filters.chat(LOOTBOT) & autocava &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=55)
async def main_menu_triggers(client, message):
	if len(LOOP) < 1 and not ESTRAZIONE_CHECK.search(message.text) and not CURRENT_MISSION_CHECK.search(message.text) \
			and not CURRENT_CAVA_CHECK.search(message.text) and not CURRENT_INCARICO_CHECK.search(message.text):
		LOOP.add_task(create_task("Got spare time for a cava?", client=client)(esplorazioni))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai completato l'esplorazione della cava"), group=55)
async def riavvia_cava(client, message):
	await asyncio.sleep(1) # The "daily done" msg comes after, so let's give lootbot 1 sec to send it
	LOOP.state["dungeon"]["interrupt"] = True
	if (CONFIG["cava"]["auto"] or autocava_check()):
		LOOP.add_task(create_task("Riavvia cava", client=client)(esplorazioni))
	elif CONFIG["talismani"]:
		@create_task("Equipaggia Talismano Oculato", client=client)
		async def equip_talismano_oculato(ctx):
			await ctx.client.send_message(LOOTBOT, "Equipaggia Talismano Oculato")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(equip_talismano_oculato)

@alemiBot.on_message(filters.chat(LOOTBOT) & autocava & filters.regex(pattern=r"Non puoi andare in esplorazione"), group=55)
async def cant_restart_cava(client, message):
	LOOP.add_task(create_task("Non posso fare cave ora", client=client)(mnu), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & autocava & filters.regex(pattern=r"Seleziona il viaggio o la cava da esplorare"), group=55)
async def scegli_cava(client, message):
	kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
	dest = CONFIG["cava"]["name"]
	for btn in kb:
		if dest.lower() in btn.lower():
			dest = btn
			break
	@create_task(f"Scegli cava {CONFIG['cava']['name']}", client=client, dest=dest)
	async def start_cava(ctx):
		await ctx.client.send_message(LOOTBOT, ctx.dest)
	LOOP.add_task(start_cava, prio=True)

TALISMAN_CHECK = re.compile(r"Talismano bonus pietre: (?P<status>❌|✅)")
RETURN_CHECK = re.compile(r"Puoi tornare ancora da (?P<viaggi>[0-9]+) viaggi e (?P<cave>[0-9]+) cave")
@alemiBot.on_message(filters.chat(LOOTBOT) & autocava & filters.regex(pattern=r"Iniziare il viaggio?"), group=55)
async def check_amuleto(client, message):
	m = RETURN_CHECK.search(message.text)
	if m:
		LOOP.state["esplorazioni"]["ritorni"]["cava"] = int(m["cave"])
		LOOP.state["esplorazioni"]["ritorni"]["viaggio"] = int(m["viaggi"])
	if CONFIG["talismani"] and TALISMAN_CHECK.search(message.text)["status"] == "❌":
		@create_task("Equipaggia Talismano Famelico", client=client)
		async def equip_talismano_famelico(ctx):
			await ctx.client.send_message(LOOTBOT, "Equipaggia Talismano Famelico")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(equip_talismano_famelico, prio=True)
		LOOP.state["talisman-lock"] = True
	else:
		LOOP.add_task(create_task("Ok, avvia cava", client=client)(si), prio=True)

DIMEZZATO_CHECK = re.compile(r"dimezzat.!")
@alemiBot.on_message(filters.chat(LOOTBOT) & autocava & filters.regex(pattern=r"(?:[^ ]+), ti aspetta (?P<loc>un'esplorazione|un incredibile viaggio)"), group=55)
async def gemma_la_cava(client, message): # TODO allow to retreat from exploration rather than using gems!
	loc = "cava" if message.matches[0]["loc"] == "un'esplorazione" else "viaggio"
	dimezzato = DIMEZZATO_CHECK.search(message.text)
	skip = (not dimezzato or CONFIG["cava"]["halvedskip"]) and CONFIG["cava"]["skip"] and LOOP.state["gemme"] != {} \
						and LOOP.state["gemme"] > CONFIG["gem-limit"]
	ritorna = "Indecisione" in LOOP.state["imprese"]["todo"] or (not dimezzato and
				(CONFIG["cava"]["ritorna"] or "Quanta fretta" in LOOP.state["imprese"]["todo"]) 
					and LOOP.state["esplorazioni"]["ritorni"][loc] > 0)
	if ritorna:
		@create_task("Ritorna dall'esplorazione", client=client)
		async def return_from_exploration(ctx):
			await ctx.client.send_message(LOOTBOT, "Ritorna")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(return_from_exploration, prio=True)
	elif skip:
		@create_task("Gemma l'esplorazione", client=client)
		async def gem_cava(ctx):
			await ctx.client.send_message(LOOTBOT, "Concludi immediatamente")
		LOOP.add_task(gem_cava, prio=True)
	else:
		LOOP.add_task(create_task("Aspetta l'esplorazione", client=client)(mnu))
			
@alemiBot.on_message(filters.chat(LOOTBOT) & autocava & filters.regex(
	pattern=r"Sicuro di voler terminare subito l'esplorazione della cava\? Ti costerà (?P<costo>[^ ]+) 💎\. Ne possiedi (?P<gemme>[0-9\.]+)"
), group=55)
async def aggiorna_numero_gemme(client, message):
	cost = 4
	if message.matches[0]["costo"] == "una":
		cost = 1
	elif message.matches[0]["costo"] == "due":
		cost = 2
	elif message.matches[0]["costo"] == "tre":
		cost = 3
	elif message.matches[0]["costo"].isnumeric():
		cost = int(message.matches[0]["costo"])

	curr_gem = int(message.matches[0]["gemme"].replace(".", ""))

	if CONFIG["cava"]["skip"] and curr_gem - cost > CONFIG["gem-limit"]:
		@create_task("Conferma di gemmare la cava", client=client)
		async def confirm_gemmare_cava(ctx):
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(confirm_gemmare_cava, prio=True)
		LOOP.state["gemme"] = curr_gem - cost
	else:
		LOOP.state["gemme"] = curr_gem
		LOOP.add_task(create_task("Non abbastanza gemme per gemmare", client=client)(mnu), prio=True)
