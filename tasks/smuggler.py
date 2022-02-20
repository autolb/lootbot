import re
import time
import asyncio

from pyrogram import filters

from alemibot import alemiBot

from ..common import LOOTBOT, CRAFTLOOTBOT, random_wait, CONFIG, Priorities as P
from ..tasks import mnu, si
from ..loop import LOOP, create_task

from .craft import craft_sync, craft_quick

# Requires client
async def contrabbandiere(ctx):
	await ctx.client.send_message(LOOTBOT, "Piazza 💰")
	await random_wait()
	await ctx.client.send_message(LOOTBOT, "Contrabbandiere dell'Est 🔩")

OFFERTA_CONTRABBANDIERE = re.compile(r"🔩 Offerta Contrabbandiere disponibile")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"
), group=P.contr)
async def vai_al_contrabbandiere(client, message):
	if CONFIG()["contrabbandiere"] and not LOOP.state["smuggler"]["cant-craft"] \
	and OFFERTA_CONTRABBANDIERE.search(message.text) and len(LOOP) == 0:
		LOOP.add_task(create_task("Offerta contrabbandiere disponibile", client=client)(contrabbandiere))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Il Contrabbandiere ha una nuova offerta per te!"), group=P.contr)
async def nuovo_contrabbandiere(client, message):
	if CONFIG()["contrabbandiere"]:
		LOOP.add_task(create_task("Nuova offerta Contrabbandiere", client=client)(contrabbandiere))
	LOOP.state["smuggler"]["try-craft-once"] = False
	LOOP.state["smuggler"]["cant-craft"] = False

ITEM_SEARCH = re.compile(r"quando torna ti propone affari diversi\.\n\n(?P<item>.*) \((?P<rarity>.+)\) al prezzo di (?P<price>[0-9\.]+) §(?: |)(?P<status>✅|☑️|)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Benvenut. (?:.*)!\nPuoi creare oggetti per il Contrabbandiere"
), group=P.contr)
async def schermata_contrabbandiere(client, message):
	if CONFIG()["contrabbandiere"]:
		match = ITEM_SEARCH.search(message.text)
		if match:
			s = match["status"]
			accept = message.reply_markup.keyboard[0][0]
			if s == "✅": # done
				@create_task("Accetta offerta", client=client, text=accept)
				async def accetta_offerta(ctx):
					await ctx.client.send_message(LOOTBOT, ctx.text)
					await random_wait()
					await si(ctx)
					await random_wait()
					await mnu(ctx)
				LOOP.add_task(accetta_offerta, prio=True)
				LOOP.state["smuggler"]["try-craft-once"] = False
				LOOP.state["smuggler"]["cant-craft"] = False
			elif not LOOP.state["smuggler"]["try-craft-once"]: # full craft
				LOOP.state["smuggler"]["try-craft-once"] = True
				if match["status"] == "☑️":
					LOOP.add_task(create_task(f"Crea {match['item']} (1 step) per Contrabbandiere",
									client=client, item=match["item"])(craft_quick))
				else:
					LOOP.add_task(create_task(f"Crea {match['item']} per Contrabbandiere",
									 client=client, recipe=match["item"])(craft_sync))
			else:
				LOOP.state["smuggler"]["cant-craft"] = True
				LOOP.add_task(create_task("Impossibile completare offerta contrabbandiere", client=client)(mnu))
