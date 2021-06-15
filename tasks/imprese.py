import re

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, random_wait, CONFIG
from plugins.lootbot.tasks import mnu, si
from plugins.lootbot.loop import LOOP, create_task

from plugins.lootbot.tasks.craft import craft_sync

IMPRESE = {
	"Ficcanaso" : "Spiare giocatori (non dal plus)",
	"Avanti nel tempo" : "Utilizzare Varco temporale",
	"Mucchio di pietre" : "Raddoppiare pietre del drago in cava",
	"Crittatore" : "Attivare turni di vulnerabilita` contro mob",
	"Nuove Terre" : "Accedi ad una istanza gia` generata di un dungeon",
	"In allenamento!" : "Gioca un allenamento sulle Mappe",
	"Il mio esercito": "Manda Piedelesto in Ispezione",
	"Ispezione accurata": "Manda Occhiofurbo in Ispezione",
	"Ispezione modesta": "Manda Testacalda in Ispezione"
}

DAILY_CHECK = re.compile(r"(?:Imprese:|(?P<name>.*) \((?P<curr>[0-9]+)\/(?P<top>[0-9]+)\)) (?P<state>🏁|[✅❌ ]+)")
@alemiBot.on_message(filters.chat(LOOTBOT) &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=30) # Do this before dungeons or inspections!
async def main_menu_triggers(client, message):
	cfg = CONFIG.get()
	if len(LOOP) < 1 and cfg["imprese"]["auto"] and LOOP.state["imprese"]["new"]:
		LOOP.state["imprese"]["new"] = False
		match = DAILY_CHECK.search(message.text)
		if match and match["state"] != "🏁":
			@create_task("Controlla Imprese", client=client)
			async def check_dailies(ctx):
				await ctx.client.send_message(LOOTBOT, "Imprese 🏋️")
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(check_dailies)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai completato l'impresa giornaliera (?P<name>.*) e hai"), group=58)
async def on_daily_completed(client, message):
	cfg = CONFIG.get()
	name = message.matches[0]["name"]
	if name in LOOP.state["imprese"]["todo"]:
		LOOP.state["imprese"]["todo"].remove(name)
	if cfg["imprese"]["single"] and name == "Arte della guerra":  # reequip what you had
		@create_task("Rivestiti", client=client)
		async def dress_up(ctx):
			for item in ctx.state["imprese"]["prev-equip"]:
				await ctx.client.send_message(LOOTBOT, f"Equipaggia {item}")
				await random_wait()
				await si(ctx)
			ctx.state["imprese"]["prev-equip"] = {}
			ctx.state["imprese"]["naked"] = False
			await mnu(ctx)
		LOOP.add_task(dress_up)


@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Imprese giornaliere\nOggi non sono disponibili imprese giornaliere :\("), group=58)
async def no_dailies_on_weekend(client, message):
	LOOP.state["imprese"]["todo"] = []

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Imprese giornaliere\n" +
			r"> (?P<done1>✅ |)(?P<title1>.*): (?P<n1>[0-9\.]+)(?:\/|)(?P<max1>[0-9\.]+|) (?P<desc1>.*) \((?P<reward1>[0-9\.]+ §)\)\n" +
			r"> (?P<done2>✅ |)(?P<title2>.*): (?P<n2>[0-9\.]+)(?:\/|)(?P<max2>[0-9\.]+|) (?P<desc2>.*) \((?P<reward2>[0-9\.]+ §)\)\n" +
			r"> (?P<done3>✅ |)(?P<title3>.*): (?P<n3>[0-9\.]+)(?:\/|)(?P<max3>[0-9\.]+|) (?P<desc3>.*) \((?P<reward3>[0-9\.]+ §)\)\n" +
			r"\nImprese complessive"
), group=58)
async def salva_imprese_di_oggi(client, message):
	match = message.matches[0].groupdict()
	cfg = CONFIG.get()
	LOOP.state["imprese"]["giornaliere"] = [
		{
			"title" : match["title1"],
			"done" : match["done1"] == "✅ ",
			"amount" : int(match["n1"].replace(".","")),
			"required" : int(match["max1"].replace(".","")) if match["max1"] != "" else 1,
			"text" : match["desc1"],
			"reward" : match["reward1"]
		},{
			"title" : match["title2"],
			"done" : match["done2"] == "✅ ",
			"amount" : int(match["n2"].replace(".","")),
			"required" : int(match["max2"].replace(".","")) if match["max2"] != "" else 1,
			"text" : match["desc2"],
			"reward" : match["reward2"]
		},{
			"title" : match["title3"],
			"done" : match["done3"] == "✅ ",
			"amount" : int(match["n3"].replace(".","")),
			"required" : int(match["max3"].replace(".","")) if match["max3"] != "" else 1,
			"text" : match["desc3"],
			"reward" : match["reward3"]
		}
	]
	LOOP.state["imprese"]["todo"] = []
	LOOP.state["once"] = []
	for im in LOOP.state["imprese"]["giornaliere"]:
		if not im["done"]:
			LOOP.state["imprese"]["todo"].append(im["title"])
	if cfg["imprese"]["single"]:
		if "Armaiolo monotono" in LOOP.state["imprese"]["todo"]:
			n = 50
			for d in LOOP.state["imprese"]["giornaliere"]:
				if d["title"] == "Armaiolo monotono":
					n = d["required"]
					break
			LOOP.add_task(create_task("Crea Cerbottana per armaiolo monotono",
							client=client, recipe=f"Cerbottana:{n}")(craft_sync))
		if "Ordigni pronti UR" in LOOP.state["imprese"]["todo"]:
			n = 15
			for d in LOOP.state["imprese"]["giornaliere"]:
				if d["title"] == "Ordigni pronti UR":
					n = d["required"]
					break
			LOOP.add_task(create_task("Crea Caccia di Carta per Ordigni pronti UR",
							client=client, recipe=f"Caccia di Carta:{n}")(craft_sync))
		if "Nutri il drago" in LOOP.state["imprese"]["todo"] \
		and LOOP.state["me"]["dragon"]["lvl"] in [100, 200, 300]:
			@create_task("Prova a nutrire il drago", client=client)
			async def try_feed(ctx):
				await ctx.client.send_message(LOOTBOT, "Giocatore 👤")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Drago 🐉")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Dai tutte tranne epiche")
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(try_feed)
		if "Pazzo come il mercante" in LOOP.state["imprese"]["todo"]:
			@create_task("Compra un pacchetto dal mercante", client=client)
			async def buy_pack(ctx):
				await ctx.client.send_message(LOOTBOT, "Piazza 💰")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Mercante Pazzo 👝")
				await random_wait()
			LOOP.add_task(buy_pack)
		if "Arte della guerra" in LOOP.state["imprese"]["todo"]:
			@create_task("Spogliati ( ͡° ͜ʖ ͡°)", client=client)
			async def get_naked(ctx):
				await ctx.client.send_message(LOOTBOT, "Zaino 🎒")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Rimuovi 🚫")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Rimuovi Tutto")
				await random_wait()
				await si(ctx)
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(get_naked)
		if "Giocatore talentuoso" in LOOP.state["imprese"]["todo"] \
		and "Giocatore talentuoso" not in LOOP.state["once"]:
			@create_task("Apri menu talenti", client=client)
			async def open_talenti(ctx):
				await ctx.client.send_message(LOOTBOT, "Giocatore 👤")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Albero Talenti 🌳")
				await random_wait()
				await mnu(ctx)
				LOOP.state["once"].append("Giocatore talentuoso")
			LOOP.add_task(open_talenti)

PRICE_CHECK = re.compile(r"Pacchetto (?:Epici|Leggendari|Ultra Rari|Rari|Non Comuni|Comuni) \((?P<price>[0-9\.]+) §\)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Il Mercante Pazzo oggi offre"), group=58)
async def buy_cheapest_pack_from_mercante_pazzo(client, message):
	kb = [ btn for sub in message.reply_markup.keyboard for btn in sub ]
	min_price = 1000000000 # You can't hold more money than this anyway
	pacchetto = "Pacchetto Epici"
	for btn in kb:
		match = PRICE_CHECK.search(btn)
		if match:
			cost = int(match["price"].replace(".", ""))
			if cost < min_price:
				min_price = cost
				pacchetto = btn
	if "Pazzo come il mercante" in LOOP.state["imprese"]["todo"]:
		@create_task("Compra {pacchetto}", client=client, pack=pacchetto)
		async def buy_cheapest_pacchetto(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.pack)
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Accetta")
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(buy_cheapest_pacchetto, prio=True)
			
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"> Arma \((?P<arma>.*)\)\n" +
			r"> Armatura \((?P<armatura>.*)\)\n" +
			r"> Scudo \((?P<scudo>.*)\)\n" +
			r"(?:> Talismano \((?P<talismano>.*)\)\n|)\n" +
			r"Rimossi e reinseriti nello zaino"
), group=58)
async def got_naked_message(client, message):
	"""This is kind of an ad-hoc hook for "Arte della Guerra" """
	cfg = CONFIG.get()
	if "Arte della guerra" in LOOP.state["imprese"]["todo"]:
		LOOP.state["imprese"]["prev-equip"] = [
			message.matches[0]["arma"],
			message.matches[0]["armatura"],
			message.matches[0]["scudo"]
		]
		LOOP.state["imprese"]["naked"] = True
		if cfg["talismani"]:
			@create_task("Rimettiti subito il talismano", client=client, item=message.matches[0]['talismano'])
			async def rimetti_talismano(ctx):
				await ctx.client.send_message(LOOTBOT, f"Equipaggia {ctx.item}")
				await random_wait()
				await si(ctx)
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(rimetti_talismano)
		else:
			LOOP.state["imprese"]["prev-equip"].append(message.matches[0]['talismano'])
