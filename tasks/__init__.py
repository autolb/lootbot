import re

from plugins.lootbot.common import LOOTBOT, random_wait
"""
Some sample tasks you can directly await with current context in
your tasks or make small tasks of.
"""
# Requires client, text
async def loot_message(ctx):
	await ctx.client.send_message(LOOTBOT, ctx.text)

# Requires client
async def si(ctx):
	await ctx.client.send_message(LOOTBOT, "Si")

# Requires client
async def no(ctx):
	await ctx.client.send_message(LOOTBOT, "No")

# Requires client
async def mnu(ctx):
	await ctx.client.send_message(LOOTBOT, "Torna al menu")

# Requires client
async def rifugio(ctx):
	await ctx.client.send_message(LOOTBOT, "Torna al Rifugio")

# Requires client
async def emporio(ctx):
	await ctx.client.send_message(LOOTBOT, "Emporio")
