import re

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, random_wait, CONFIG
from plugins.lootbot.tasks import si, mnu
from plugins.lootbot.loop import LOOP, create_task

CFG = CONFIG.get("assalto")

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"(?P<monster>.*) ha raggiunto la magione, entra in battaglia e difendila prima che venga distrutta!"
), group=54)
async def battaglia(client, message):
	LOOP.state["dungeon"]["interrupt"] = True
	if CFG["auto"]:
		role = CFG["ruolo"]
		if not role:
			@create_task("Incrementa Assalto", client=client)
			async def incrementa(ctx):
				await ctx.client.send_message(LOOTBOT, "Riprendi battaglia ☄️")
				await random_wait()
				await ctx.client.send_message(LOOTBOT, "Incremento 💢")
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(incrementa)
		else:
			pass # TODO altri ruoli

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"L'eletto ti incita ad attivare l'incremento per l'assalto!"), group=54)
async def forgot_to_increment(client, message):
	LOOP.state["dungeon"]["interrupt"] = True
	if CFG["auto"]:
		@create_task("Incrementa Assalto (richiesto)", client=client)
		async def incrementa(ctx):
			await ctx.client.send_message(LOOTBOT, "Riprendi battaglia ☄️")
			await random_wait()
			await ctx.client.send_message(LOOTBOT, "Incremento 💢")
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(incrementa)
