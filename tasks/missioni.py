import re
import asyncio

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, random_wait, CONFIG, Rarity
from plugins.lootbot.tasks import si, mnu
from plugins.lootbot.loop import LOOP, create_task

def automission_check():
	return (CONFIG()["mission"]["auto"] or
			(CONFIG()["imprese"]["activity"] and
				("Esploratore pazzo" in LOOP.state["imprese"]["todo"] or
				 "Che fortuna!" in LOOP.state["imprese"]["todo"] or
				 "Evoluzione" in LOOP.state["imprese"]["todo"] or
				 "Avventura interminabile" in LOOP.state["imprese"]["todo"] or
				 "Missioni per sempre" in LOOP.state["imprese"]["todo"])))

automission = filters.create(lambda _, __, ___: automission_check())

# Requires client
async def missione(ctx):
	await ctx.client.send_message(LOOTBOT, "⚔️ Missione ⚔️")

CURRENT_MISSION_CHECK = re.compile(r"Missione fino")
CURRENT_INCARICO_CHECK = re.compile(r"Incarico in corso fino")
CURRENT_CAVA_CHECK = re.compile(r"(?:🗻 Esplorazione cava|🧗 Viaggio) fino")
CURRENT_ITINERARIO_CHECK = re.compile(r"🗾 Itinerario fino")
@alemiBot.on_message(filters.chat(LOOTBOT) & automission &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=52)
async def main_menu_triggers(client, message):
	if len(LOOP) < 1 and not CURRENT_MISSION_CHECK.search(message.text) \
			and not CURRENT_ITINERARIO_CHECK.search(message.text) and not CURRENT_CAVA_CHECK.search(message.text) \
																  and not CURRENT_INCARICO_CHECK.search(message.text):
		LOOP.add_task(create_task("Got spare time for a mission?", client=client)(missione))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Missione completata! Hai ottenuto:"), group=52)
async def missione_finita(client, message):
	await asyncio.sleep(1) # The "daily done" message comes after the "mission done" message. Wait for it to process
	rarity = re.search("rarità (?P<rarity>C|NC|R|UR|L|E)", message.text)["rarity"]
	LOOP.state["mission"]["rarity"] = rarity
	if automission_check():
		LOOP.state["dungeon"]["interrupt"] = True
		LOOP.add_task(create_task("Riavvia missione", client=client)(missione))
	elif CONFIG()["talismani"] and LOOP.state["mission"]["talisman"]:
		@create_task("Equipaggia Talismano Oculato", client=client)
		async def equip_talismano_oculato(ctx):
			await ctx.client.send_message(LOOTBOT, "Equipaggia Talismano Oculato")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(equip_talismano_oculato)
		LOOP.state["mission"]["talisman"] = False

@alemiBot.on_message(filters.chat(LOOTBOT) & automission & filters.regex(pattern=r"Prima di poter partire in un'avventurosa missione"), group=52)
async def cant_restart_mission(client, message):
	LOOP.add_task(create_task("Non posso fare missioni ora", client=client)(mnu), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & automission & filters.regex(
	pattern=r".*(?:È un umile missione quella che t'è stata assegnata|" +
			r"È una missione banale, quella che ti è stata affidata|" +
			r"È un antica mappa quella che t'è capitata tra le mani...|" +
			r"È una mappa di straordinario valore quella che t'è capitata tra le mani...|" +
			r"Finalmente le tue gesta sono state riconosciute! Ti è stata assegnata una missione direttamente dalla Fenice|" +
			r"Avventurieri come te vivono per giorni come questo!\nUn Epica avventura ti aspetta, finalmente...) \((?P<rarity>C|NC|R|UR|L|E)\)",
	flags=re.DOTALL
), group=52)
async def avvia_e_skippa_missione(client, message):
	if CONFIG()["talismani"] and not LOOP.state["mission"]["talisman"]:
		@create_task("Equipaggia Talismano Esploratore", client=client)
		async def equip_talismano_esploratore(ctx):
			await ctx.client.send_message(LOOTBOT, "Equipaggia Talismano Esploratore")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(equip_talismano_esploratore)
		LOOP.state["mission"]["talisman"] = True
	else:
		rarity = message.matches[0]["rarity"]
		skip_rarity = CONFIG()["mission"]["rarity"].upper()
		dont_skip = CONFIG()["imprese"]["auto"] and "Avventura interminabile" in LOOP.state["imprese"]["todo"] and Rarity[rarity] >= Rarity["UR"]
		skip = (not dont_skip and CONFIG()["mission"]["skip"] and Rarity[rarity] >= Rarity[skip_rarity]
							and LOOP.state["gemme"] != {} and LOOP.state["gemme"] > CONFIG()["gem-limit"])
		@create_task("Avvia Nuova Missione", client=client, skip=skip)
		async def start_new_mission(ctx):
			await si(ctx)
			await random_wait()
			if ctx.skip:
				await ctx.client.send_message(LOOTBOT, "Termina subito")
			else:
				await mnu(ctx)
		LOOP.add_task(start_new_mission, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & automission & filters.regex(
	pattern=r"Sicuro di voler terminare subito la missione\? Consumerai (?:.+) 💎. Ne possiedi (?P<n>[0-9\.]+)"
), group=52)
async def skip_and_menu(client, message):
	@create_task("Conferma missione gemmata", client=client)
	async def confirm_that(ctx):
		await si(ctx)
		await random_wait()
		await mnu(ctx)
	LOOP.add_task(confirm_that, prio=True)
	LOOP.state["gemme"] = int(message.matches[0]["n"]) -1

@alemiBot.on_message(filters.chat(LOOTBOT) & automission & filters.regex(pattern=r"Manca meno di 5 minuti al termine della missione"), group=50)
async def cant_skip_mission(client, message):
	LOOP.add_task(create_task("Mancano meno di 5 min", client=client)(mnu))
