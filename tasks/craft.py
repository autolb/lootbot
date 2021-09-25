import re
import time
import asyncio

from pyrogram import filters

from bot import alemiBot

from util.command import filterCommand
from util.permission import is_superuser
from util.message import edit_or_reply

from plugins.lootbot.common import LOOTBOT, CRAFTLOOTBOT, random_wait, CONFIG, Priorities as P
from plugins.lootbot.tasks import mnu
from plugins.lootbot.loop import LOOP, create_task

CRAFT_MSG = None

# with open("data/recipes.json") as f:
#	  RECIPES = json.load(f)
# 
# def expand_recipes(curr, inventory, buf):
#	  global RECIPES
#	  if curr.lower() not in RECIPES:
#		  buf.append(curr)
#		  return buf
#	  if 
#	  for el in RECIPES[curr.lower()]:
#		  expand_recipes(el, buf)
#	  return buf
# 
# def get_list(needed, inventory):
#	  global RECIPES
#	  if needed.lower() not in RECIPES:
#		  raise KeyError("No recipe for item")
#	  craftlist = expand_recipes(needed.lower(), [])
#	  if any(el not in inventory for el in craftlist):
		

# Requires client
async def sync_inventory(ctx):
	await ctx.client.send_message(CRAFTLOOTBOT, "/svuota")
	await random_wait()
	await ctx.client.send_message(CRAFTLOOTBOT, "/salvazaino")
	await random_wait()
	ctx.state["craft"]["fwd"] = True
	await ctx.client.send_message(LOOTBOT, "zaino completo")
	await asyncio.sleep(CONFIG()["wait"]["forward-cd"]) # give some time to other handlers to handle this
	ctx.state["craft"]["fwd"] = False
	await ctx.client.send_message(LOOTBOT, "Torna al menu")
	await ctx.client.send_message(CRAFTLOOTBOT, "Salva")
	await asyncio.sleep(CONFIG()["wait"]["forward-cd"]) # Give some time to CLB to save backpack

# Requires client, item
async def craft_quick(ctx): # This will be nicer once we don't need CraftLootBot anymore
	ctx.state["craft"]["ongoing"] = True
	ctx.state["craft"]["list"] = [ f"Crea {ctx.item}" ]
	ctx.state["craft"]["index"] = 0
	ctx.state["craft"]["total"] = 1
	await craft_loop(ctx)

# Requires client, recipe
async def craft(ctx):
	ctx.state["craft"]["ongoing"] = True
	await ctx.client.send_message(CRAFTLOOTBOT, f"/craft {ctx.recipe}")

# Requires client, recipe
async def craft_sync(ctx):
	global CRAFT_MSG
	await sync_inventory(ctx)
	if CRAFT_MSG:
		CRAFT_MSG = await edit_or_reply(CRAFT_MSG, "<code>→ </code> Synched inventory", parse_mode="html")
	await craft(ctx)
	if CRAFT_MSG:
		CRAFT_MSG = await edit_or_reply(CRAFT_MSG, "<code>→ </code> Started craft loop", parse_mode="html")

# Requires client, message
async def craft_loop(ctx):
	recipe = ctx.state["craft"]["list"][0]
	await ctx.client.send_message(LOOTBOT, recipe)

# Requires client
async def procedi(ctx):
	await ctx.client.send_message(LOOTBOT, "Procedi")

# Auto Craft
@alemiBot.on_message(~filters.chat(CRAFTLOOTBOT) & is_superuser & filterCommand(["lcraft", "craft"], list(alemiBot.prefixes),
																		flags=["-loop", "-sync", "-craft", "-stop", "-nomsg"]))
async def auto_craft(client, message):
	global CRAFT_MSG
	no_msg = bool(message.command["-nomsg"])
	if message.command["-stop"]:
		LOOP.state["craft"]["ongoing"] = False
		curr = LOOP.state["craft"]["list"][0]
		i = LOOP.state["craft"]["index"]
		tot = LOOP.state["craft"]["total"]
		if CRAFT_MSG:
			await edit_or_reply(CRAFT_MSG, f"<code>[!] → </code> Stopped <code>{curr}</code> [<code>{i}/{tot}</code>]", parse_mode="html")
	elif message.command["-loop"]:
		LOOP.add_task(create_task(f"Craft loop (forced)", client=client)(craft_loop))
		CRAFT_MSG = await edit_or_reply(message, "<code>→ </code> Force started craft loop", parse_mode="html")
	elif message.command["-sync"]:
		LOOP.add_task(create_task("Sync with CraftLootBot", client=client)(sync_inventory))
		CRAFT_MSG = await edit_or_reply(message, "<code> → </code> Synching inventory (no craft)", parse_mode="html")
	elif len(message.command) < 1:
		return await edit_or_reply(message, "<code>[!] → </code> No arg given", parse_mode="html")
	elif message.command["-craft"]:
		target = message.command.text
		LOOP.add_task(create_task(f"Craft {target} (nosync)", client=client, recipe=message.command.text)(craft))
		CRAFT_MSG = await edit_or_reply(message, "<code>→ </code> Started craft loop (no sync)", parse_mode="html")
	else:
		target = message.command.text
		LOOP.add_task(create_task(f"Craft {target}", client=client, recipe=target)(craft_sync))
		CRAFT_MSG = await edit_or_reply(message, "<code>→ </code> Synching inventory", parse_mode="html")
	if no_msg:
		CRAFT_MSG = None

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"La tua rinascita non è sufficente per creare questo oggetto"), group=P.craft)
async def rinascita_insufficiente(client, message):
	LOOP.state["craft"]["ongoing"] = False

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Creazione (?P<amount>[0-9]+)x (?P<recipe>.*)\nSpenderai (?P<cost>[0-9\.]+) §"
), group=P.craft)
async def craft_confirmation(client, message):
	global CRAFT_MSG
	if LOOP.state["craft"]["ongoing"]:
		curr = LOOP.state["craft"]["list"].pop(0)
		LOOP.state["craft"]["index"] += 1
		match = message.matches[0]
		if int(match["cost"].replace(".", "")) > LOOP.state["cash"] or "🚫" in message.text:
			LOOP.state["craft"]["ongoing"] = False
			LOOP.add_task(create_task("Craft interrotto", client=client)(mnu), prio=True)
			if CRAFT_MSG:
				i = LOOP.state["craft"]["index"]
				tot = LOOP.state["craft"]["total"]
				await edit_or_reply(CRAFT_MSG, f"<code>[!] → </code> <b>Failed</b> <b>{curr}</b> [<code>{i}/{tot}</code>]", parse_mode="html")
				CRAFT_MSG = None
			if CONFIG()["log"]["pin"]["craft"]:
				await message.pin()
		else:
			LOOP.add_task(create_task(f"Procedi - {curr}", client=client)(procedi), prio=True)
			if len(LOOP.state["craft"]["list"]) > 0:
				LOOP.add_task(create_task("Craft loop", client=client)(craft_loop))
				if CRAFT_MSG:
					i = LOOP.state["craft"]["index"]
					tot = LOOP.state["craft"]["total"]
					CRAFT_MSG = await edit_or_reply(CRAFT_MSG, f"<code> → </code> <b>{curr}</b> [<code>{i}/{tot}</code>]", parse_mode="html")
			else:
				LOOP.state["craft"]["ongoing"] = False
				LOOP.add_task(create_task("Craft finished", client=client)(mnu))
				if CRAFT_MSG:
					tot = LOOP.state["craft"]["total"]
					i = LOOP.state["craft"]["index"]
					await edit_or_reply(CRAFT_MSG,
							f"<code> → </code> <b>{curr}</b> [<code>{i}/{tot}</code>]\n<code>→ </code> Done (<code>{tot}</code> crafted)",
							parse_mode="html")
					CRAFT_MSG = None

FULL_BACKPACK_CHECK = re.compile(r"([^ ]+), ecco il contenuto del tuo zaino:")
@alemiBot.on_message(filters.chat(LOOTBOT), group=2**16) # trigger always, don't overrule shit
async def callback_triggers(client, message):
	if not LOOP.state["craft"]["last-fwd"]:
		LOOP.state["craft"]["last-fwd"] = 0
	if LOOP.state["craft"]["fwd"]: # Automatically forward your inventory to craftlootbot
		if FULL_BACKPACK_CHECK.search(message.text):
			LOOP.state["craft"]["last-fwd"] = time.time()
			await message.forward(CRAFTLOOTBOT)
		elif time.time() - LOOP.state["craft"]["last-fwd"] < 2 \
		and message.text.count(">") > 1:
			LOOP.state["craft"]["last-fwd"] = time.time()
			await message.forward(CRAFTLOOTBOT)

BUTTON_CHECK = re.compile(r"Scegli come ottenere la lista craft:")
@alemiBot.on_message(filters.chat(CRAFTLOOTBOT), group=P.craft)
async def craftlootbot_triggers(client, message):
	if LOOP.state["craft"]["ongoing"]:
		if message.text and BUTTON_CHECK.search(message.text):
			try:
				await message.click(x=0, timeout=0)
			except: # ignore
				pass
		elif message.media and message.document \
		and message.document.file_name == "Lista Craft.txt":
			fpath = await client.download_media(message, file_name="data/craftlist.txt")
			with open(fpath) as f:
				craft_list = f.read().strip().split("\n")[1:]
			LOOP.state["craft"]["list"] = craft_list
			LOOP.state["craft"]["index"] = 0
			LOOP.state["craft"]["total"] = len(craft_list)
			LOOP.add_task(create_task(f"Craft loop (initial)", client=client)(craft_loop))
