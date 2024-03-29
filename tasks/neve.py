import re

from pyrogram import filters

from alemibot import alemiBot
from alemibot.util import sudo, edit_or_reply, filterCommand
from alemibot.util.command import _Message as Message

from ..tasks import mnu
from ..common import LOOTBOT, random_wait, CONFIG, Priorities as P
from ..loop import LOOP, create_task

MSG = None

# Requires client
async def return_to_casadineve(ctx):
	await ctx.client.send_message(LOOTBOT, "🎄 Villaggio Innevato (Evento) 🌨")

@alemiBot.on_message(~filters.chat(LOOTBOT) & sudo & filterCommand(["lpalle", "lneve"], flags=["-stop"]))
async def auto_palle_neve(client:alemiBot, message:Message):
	global MSG
	if message.command["-stop"]:
		LOOP.state["snow"]["target"] = None
		LOOP.add_task(create_task("Palle di neve interrotte", client=client)(mnu))
		await edit_or_reply(message, "` → ` Stopped current loop")
	elif len(message.command) < 1:
		await edit_or_reply(message, "`[!] → ` No target given")
	else:
		target = message.command[0]
		if target.startswith("@"):
			target = target[1:]
		LOOP.state["snow"]["target"] = target
		LOOP.state["snow"]["thrown"] = 0
		LOOP.add_task(create_task("Inizia strage palle di neve", client=client)(return_to_casadineve))
		MSG = await edit_or_reply(message, "` → ` Avvio loop in corso...")

@alemiBot.on_message(filters.chat(LOOTBOT) &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=P.snow)
async def tornato_al_menu(client, message):
	if LOOP.state["snow"]["target"]:
		LOOP.add_task(create_task("Torna alla casa", client=client)(return_to_casadineve))

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Benvenuto nella tua Casa nella Neve 🌨"), group=P.snow)
async def tira_palla_neve(client, message):
	target = LOOP.state["snow"]["target"]
	if target:
		@create_task(f"Lancia Palla di Neve", client=client)
		async def throw_snowball(ctx):
			await ctx.client.send_message(LOOTBOT, "Lancia Palla di Neve ❄️")
		LOOP.add_task(throw_snowball, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Non hai abbastanza Palle di Neve!"), group=P.snow)
async def no_palle_neve(client, message):
	LOOP.state["snow"]["target"] = None
	LOOP.add_task(create_task("Palle di neve insufficienti", client=client)(mnu), prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Puoi lanciare una Palla di Neve ad un giocatore in particolare"), group=P.snow)
async def scegli_bersaglio_palla_neve(client, message):
	target = LOOP.state["snow"]["target"]
	if target:
		@create_task(f"Lancia Palla contro {target}", client=client, target=target)
		async def choose_ball_target(ctx):
			await ctx.client.send_message(LOOTBOT, ctx.target)
		LOOP.add_task(choose_ball_target, prio=True)

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai lanciato una Palla di Neve e hai colpito il Pupazzo di Neve di (?P<name>.+)"), group=P.snow)
async def colpito_pupazzo(client, message):
	global MSG
	target = LOOP.state["snow"]["target"]
	if target:
		@create_task("Continua a lanciare", client=client)
		async def back_to_casadineve(ctx):
			await ctx.client.send_message(LOOTBOT, "Torna alla Casa")
		LOOP.add_task(back_to_casadineve, prio=True)
		LOOP.state["snow"]["thrown"] += 2
		await MSG.edit(f"`→ ` Attacco pupazzi di **@{LOOP.state['snow']['target']}**\n` → ` Lanciate --{LOOP.state['snow']['thrown']}-- palle") 

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Hai lanciato una Palla di Neve e hai colpito (?P<name>.+) che ha perso (?P<hp>[0-9\.]+) hp"), group=P.snow)
async def uccisi_tutti_pupazzi(client, message):
	global MSG
	if LOOP.state["snow"]["target"]:
		LOOP.state["snow"]["thrown"] += 2
		target = LOOP.state["snow"]["target"]
		LOOP.state["snow"]["target"] = None
		LOOP.add_task(create_task(f"Distrutti tutti i pupazzi di {target}", client=client)(mnu), prio=True)
		await MSG.edit(f"`→ ` Attacco pupazzi di **@{target}**\n` → ` Distrutti tutti i pupazzi con --{LOOP.state['snow']['thrown']}-- palle di neve")
	
