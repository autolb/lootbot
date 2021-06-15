import re

from pyrogram import filters

from bot import alemiBot

from util.command import filterCommand
from util.permission import is_superuser
from util.message import edit_or_reply

from plugins.lootbot.common import LOOTBOT, random_wait
from plugins.lootbot.tasks import si, mnu, emporio
from plugins.lootbot.loop import LOOP, create_task

# Auto buy Forzieri
TIERS = ["Epico", "Leggendario", "di Diamante", "Prezioso", "di Ferro", "di Legno"]
@alemiBot.on_message(is_superuser & filterCommand(["forzieri", "lchest", "lch"], list(alemiBot.prefixes)))
async def auto_buy_chests(client, message):
	cfg = CONFIG.get()
	LOOP.state["auto-chest"] = True
	for tier in TIERS:
		@create_task(f"Compra Scrigni {tier}", client=client, tier=tier)
		async def compra_scrigno_tier(ctx):
			await ctx.client.send_message(LOOTBOT, f"compra Scrigno {ctx.tier}")
			await edit_or_reply(ctx.message, f"` → compra Scrigno {ctx.tier}")
			await asyncio.sleep(cfg["wait"]["forzieri-cd"])
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
), group=52)
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
