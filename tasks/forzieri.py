import re
import asyncio

from pyrogram import filters

from alemibot import alemiBot
from alemibot.util import filterCommand, edit_or_reply, sudo

from ..common import LOOTBOT, random_wait, CONFIG, Priorities as P
from ..tasks import si, mnu, emporio
from ..loop import LOOP, create_task

# Auto buy Forzieri
TIERS = ["Epico", "Leggendario", "di Diamante", "Prezioso", "di Ferro", "di Legno"]
@alemiBot.on_message(sudo & filterCommand(["forzieri", "lchest", "lch"]))
async def auto_buy_chests(client:alemiBot, message):
	LOOP.state["auto-chest"] = True
	for tier in TIERS:
		@create_task(f"Compra Scrigni {tier}", client=client, tier=tier)
		async def compra_scrigno_tier(ctx):
			await ctx.client.send_message(LOOTBOT, f"compra Scrigno {ctx.tier}")
			await edit_or_reply(ctx.message, f"` → compra Scrigno {ctx.tier}")
			await asyncio.sleep(CONFIG()["wait"]["forzieri-cd"])
		LOOP.add_task(compra_scrigno_tier)
	LOOP.add_task(create_task("Menu", client=client)(mnu))
	@create_task(f"Termina acquisti forzieri")
	async def fine_compra_forzieri(ctx):
		ctx.state["auto-chest"] = False
	LOOP.add_task(fine_compra_forzieri)
	await edit_or_reply(message, "` → ` Task added")

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=
	r"Seleziona la quantità di scrigni da acquistare, ogni scrigno costa (?P<price>[0-9\.]+) §\n" +
								r"Puoi ancora acquistarne (?P<number>[0-9\.]+) questa settimana"
), group=P.norm)
async def callback_triggers(client, message):
	if LOOP.state["auto-chest"]:
		match = message.matches[0]
		price = int(match["price"].replace(".", ""))
		number = int(match["number"].replace(".", ""))
		buy = int(min(number, LOOP.state["cash"]/price))
		if buy > 0:
			@create_task(f"Acquista {buy} scrigni", client=client, amount=buy)
			async def buy_max_possible(ctx):
				await ctx.client.send_message(LOOTBOT, str(ctx.amount))
				await random_wait()
				await si(ctx)
				await random_wait()
				await emporio(ctx)
			LOOP.state["cash"] -= (price * buy)
			LOOP.add_task(buy_max_possible, prio=True)
