import re

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, CONFIG, random_wait
from plugins.lootbot.tasks import mnu, si
from plugins.lootbot.loop import LOOP, create_task

from plugins.lootbot.tasks.dungeon import dungeon
from plugins.lootbot.tasks.missioni import missione

# Extra estrazione
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Durante l'estrazione di Mana trovi una vena più ricca del solito!"), group=71)
async def estrazione_extra(client, message):
	if CONFIG()["raccogli"]:
		@create_task("Estrazione extra", client=client)
		async def scava_bonus(ctx):
			await ctx.client.send_message(LOOTBOT, "Scava")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(scava_bonus)

# Extra Cariche Esplorative
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Durante l'esplorazione del Dungeon trovi una piccola boccetta"), group=71)
async def cariche_extra(client, message):
	if CONFIG()["raccogli"]:
		@create_task("Cariche extra", client=client)
		async def cariche_bonus(ctx):
			await ctx.client.send_message(LOOTBOT, "Ricarica")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(cariche_bonus)

# Extra polvere
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Durante la produzione del generatore arriva una folata di vento"), group=71)
async def polvere_extra(client, message):
	if CONFIG()["raccogli"]:
		@create_task("Polvere extra", client=client)
		async def polvere_bonus(ctx):
			await ctx.client.send_message(LOOTBOT, "Spolvera")
			await random_wait()
			await si(ctx)
			await random_wait()
			await mnu(ctx)
		LOOP.add_task(polvere_bonus)
