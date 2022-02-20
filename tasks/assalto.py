import re

from pyrogram import filters

from alemibot import alemiBot

from ..common import LOOTBOT, random_wait, CONFIG, Priorities as P
from ..tasks import si, mnu
from ..loop import LOOP, create_task

# Requires client
async def incrementa(ctx):
	if CONFIG()["assalto"]["fast"]:
		await ctx.client.send_message(LOOTBOT, "inc")
	else:
		await ctx.client.send_message(LOOTBOT, "Riprendi battaglia ☄️")
		await random_wait()
		await ctx.client.send_message(LOOTBOT, "Incremento 💢")
	ctx.loop.state["assalto"]["incrementando"] = False
	await random_wait()
	await mnu(ctx)


@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"📜 Report battaglia del turno (?P<turn>[0-9]+) contro (?P<boss>.+) \((?P<type>.+)\)"
), group=P.norm)
async def report_battaglia(client, message):
	if CONFIG()["assalto"]["inc"] and not LOOP.state["assalto"]["incrementando"]:
		LOOP.state["interrupt"] = True
		LOOP.state["assalto"]["incrementando"] = True
		LOOP.add_task(create_task("Incrementa (Report)", client=client)(incrementa))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"(?P<monster>.*) ha raggiunto la magione, entra in battaglia e difendila prima che venga distrutta!"
), group=P.norm)
async def battaglia(client, message):
	if CONFIG()["assalto"]["inc"] and not LOOP.state["assalto"]["incrementando"]:
		LOOP.state["interrupt"] = True
		LOOP.state["assalto"]["incrementando"] = True
		LOOP.add_task(create_task("Incrementa (Magione)", client=client)(incrementa))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"L'eletto ti incita ad attivare l'incremento per l'assalto!"
), group=P.norm)
async def forgot_to_increment(client, message):
	if CONFIG()["assalto"]["inc"] and not LOOP.state["assalto"]["incrementando"]:
		LOOP.state["interrupt"] = True
		LOOP.state["assalto"]["incrementando"] = True
		LOOP.add_task(create_task("Incrementa (Eletto)", client=client)(incrementa))
