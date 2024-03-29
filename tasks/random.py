import re

from pyrogram import filters

from alemibot import alemiBot

from ..common import LOOTBOT, CONFIG, random_wait, Priorities as P
from ..tasks import mnu, si
from ..loop import LOOP, create_task

from .dungeon import dungeon
from .missioni import missione

# Extra estrazione
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Durante l'estrazione di Mana trovi una vena più ricca del solito!"), group=P.rand)
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
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Durante l'esplorazione del Dungeon trovi una piccola boccetta"), group=P.rand)
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
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Durante la produzione del generatore arriva una folata di vento"), group=P.rand)
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
