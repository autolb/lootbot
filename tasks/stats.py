import re
import json
import random
from datetime import datetime

import requests

from pyrogram import filters

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, CONFIG, random_wait
from plugins.lootbot.tasks import mnu, rifugio
from plugins.lootbot.loop import LOOP, create_task

from plugins.lootbot.tasks.dungeon import dungeon
from plugins.lootbot.tasks.missioni import missione

@alemiBot.on_message(group=42069)
async def sync_state(client, message):
	if not CONFIG()["sync"]["auto"]:
		return
	if LOOP.state["last-sync"] == {} \
	or datetime.fromtimestamp(message.date).date() > LOOP.state["last-sync"]:
		if LOOP.state["last-sync"] == {}:
			@create_task("Sync state", client=client)
			async def get_player_stats(ctx):
				await ctx.client.send_message(LOOTBOT, "Giocatore 👤") # sync player stats
				await random_wait()
				await mnu(ctx)
			LOOP.add_task(get_player_stats)
		LOOP.state["last-sync"] = datetime.fromtimestamp(message.date).date()
		LOOP.state["dungeon"]["usi-varchi"] = 3
		LOOP.state["ispezione"]["rimaste"] = 10
		LOOP.state["smuggler"]["try-craft-once"] = False
		LOOP.state["smuggler"]["cant-craft"] = False
		LOOP.state["imprese"]["new"] = True
		if CONFIG()["sync"]["friends"]["auto"]:
			r = requests.get(CONFIG()["sync"]["friends"]["url"])
			with open("plugins/lootbot/data/friends.json", "w") as f:
				json.dump(r.json(), f)
		with open("plugins/lootbot/data/friends.json") as f:
			LOOP.state["friends"] = json.load(f)

STATS_MENU_CHECK = re.compile(r"(?P<rinascita>✨|🔆|💫|⭐️|🌟|🎖) (?P<lvl>[0-9]+) (❤️|🧡|.) (?P<hp>[0-9\.]+)\/(?P<maxhp>[0-9\.]+)\n💰 (?P<cash>[0-9\.]+) §")
@alemiBot.on_message(filters.chat(LOOTBOT) &
	filters.regex(pattern=r"(☀️ Buongiorno|🌙 Buonasera|🌕 Salve) [a-zA-Z0-9\_]+!"), group=70)
async def main_menu_triggers(client, message):
	match = STATS_MENU_CHECK.search(message.text)
	if match:
		LOOP.state["me"]["lvl"] = int(match["lvl"])
		LOOP.state["me"]["rinascita"] = match["rinascita"]
		LOOP.state["me"]["hp"] = int(match["hp"].replace(".", ""))
		LOOP.state["me"]["maxhp"] = int(match["maxhp"].replace(".", ""))
		LOOP.state["cash"] = int(match["cash"].replace(".", ""))

STATS_CHECK = re.compile(r"⚜️ (?P<team>.*)\n(?P<rinascita>✨|🔆|💫|⭐️|🌟|🎖) (?P<lvl>[0-9\.]+) \((?P<xp>[0-9\.]+) xp\)(?: |)\n\n🏹 (?P<class>.*)\n💎 (?P<gem>[0-9\.]+) 🏆 (?:[0-9\/]+)\n💰 (?P<cash>[0-9\.]+) §\n(❤️|🧡|🖤.*) (?P<hp>[0-9\.]+) \/ (?P<maxhp>[0-9\.]+) hp\n📦 (?P<PC>[0-9\.]+) \((?P<PCweek>[0-9\.]+)\)\n")
EQUIP_CHECK = re.compile(r"Equipaggiamento ⚔️\n(?P<weap>.*)\n(?P<armor>.*)\n(?P<shield>.*)\n(?P<amulet>.*)\n\n.*🐉")
DRAGON_CHECK = re.compile(r"\n\n(?P<name>.+) (?P<type>Infernale|dei Cieli|dell'Oscurità|dei Mari|delle Montagne|dei Ghiacci) \(L(?P<lvl>[0-9\.]+)\) 🐉\nStato: (?P<status>.*)\n(?P<claw>.*)\n(?P<armor>.*)\n(?P<sign>.*)\nCritico \((?P<crit>[0-9]+%)\)\n")
ABILITIES_CHECK = re.compile(r"Altro 💱\nAbilità: (?P<abil>[0-9\.]+)\n.*\n(?:Artefatti: (?P<artifacts>[^ ]+)\n|)(?:Registrato il .*\n|)(?:Figurine diverse: (?P<figurine>.*)\n|)Rango: (?P<rankname>.*) \((?P<rank>[0-9]+)\)(?:\nIncarichi: (?P<incarichi>[0-9\.]+)(?:\n|)|)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"(?:Giocatore|Giocatrice) (?P<class>[🦊🐅🐲🦍🦅🕊	🦏🦉🐓 ]+)\n(?P<fuckcompositeemojis>🏃‍♂️|🏃‍♀️) (?P<name>[a-zA-Z0-9_]+)(?: |)(?P<title>.*)\n"
), group=70)
async def scheda_giocatore(client, message):
	if not LOOP.state["me"]["username"]:
		LOOP.state["me"]["username"] = (await client.get_me()).username
	if message.matches[0]["name"] != LOOP.state["me"]["username"]:
		return
	m = STATS_CHECK.search(message.text)
	if m:
		LOOP.state["gemme"] = int(m["gem"].replace(".", ""))
		LOOP.state["cash"] = int(m["cash"].replace(".", ""))
		me = LOOP.state["me"]
		me["hp"] = int(m["hp"].replace(".", ""))
		me["maxhp"] = int(m["maxhp"].replace(".", ""))
		me["lvl"] = int(m["lvl"].replace(".", ""))
		me["xp"] = int(m["xp"].replace(".", ""))
		me["classe"] = m["class"]
		me["classicon"] = message.matches[0]["class"]
		me["rinascita"] = m["rinascita"]
		me["PC"] = int(m["PC"].replace(".", ""))
		me["PCweek"] = int(m["PCweek"].replace(".", ""))
		me["team"] = m["team"]
	m = EQUIP_CHECK.search(message.text)
	if m:
		LOOP.state["me"]["equip"] = m.groupdict()
	m = DRAGON_CHECK.search(message.text)
	if m:
		LOOP.state["me"]["dragon"] = m.groupdict() # super lazy
		LOOP.state["me"]["dragon"]["lvl"] = int(LOOP.state["me"]["dragon"]["lvl"])
	m = ABILITIES_CHECK.search(message.text)
	if m:
		buf = m.groupdict()
		if "artifacts" in buf and buf["artifacts"] is not None:
			LOOP.state["me"]["artefatti"] = buf["artifacts"]
		if "incarichi" and buf["incarichi"] is not None:
			LOOP.state["me"]["incarichi"] = buf["incarichi"]
		LOOP.state["me"]["abilita"] = int(buf["abil"].replace(".", ""))
		LOOP.state["dungeon"]["rank"] = int(m["rank"])
		LOOP.state["me"]["dung-rank"] = m["rankname"]

BAG_CHECK = re.compile(r"Monete: (?P<cash>[0-9\.]+) §\nGemme: (?P<gem>[0-9\.]+) 💎\nChiavi Mistiche: (?P<chiavi>[0-9\.]+) 🗝\nMonete Lunari: (?P<lunari>[0-9\.]+) 🌕\nPolvere: (?P<dust>[0-9\.]+) ♨️\nValore zaino: (?P<bag>[0-9\.]+) §")
MANA_CHECK = re.compile(r"Mana:\n> (?P<blu>[0-9\.]+) Blu 🌊\n> (?P<giallo>[0-9\.]+) Giallo ⚡️\n> (?P<rosso>[0-9\.]+) Rosso 🔥\n")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"(?P<name>[^ ]+), apri il tuo zaino ed al suo interno trovi:"
), group=70)
async def zaino_giocatore(client, message):
	me = LOOP.state["me"]
	match = BAG_CHECK.search(message.text)
	if match:
		LOOP.state["cash"] = int(match["cash"].replace(".", ""))
		LOOP.state["gemme"] = int(match["gem"].replace(".", ""))
		me["chiavi"] = int(match["chiavi"].replace(".", ""))
		me["lunari"] = int(match["lunari"].replace(".", ""))
		me["polvere"] = int(match["dust"].replace(".", ""))
		me["valore-zaino"] = int(match["bag"].replace(".", ""))
	match = MANA_CHECK.search(message.text)
	if match:
		me["mana"]["blu"] = int(match["blu"].replace(".", ""))
		me["mana"]["giallo"] = int(match["giallo"].replace(".", ""))
		me["mana"]["rosso"] = int(match["rosso"].replace(".", ""))
		
MESSAGGIO_CHECK = re.compile(r"Portando con sè un messaggio su una pergamena: (?P<msg>.+)")
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Le pattuglie intorno al villaggio ci hanno avvisato che (?P<name>.+) ha spiato il tuo rifugio!"
), group=70)
async def spiata(client, message):
	if CONFIG()["log"]["pin"]["spy"]:
		await message.pin()
	if CONFIG()["log"]["msg"]["spy"] and CONFIG()["log"]["group"]:
		name = message.matches[0]["name"]
		if name != "qualcuno":
			name = "@" + name
		text = f"`→ ` Spiato da **{name}**"
		match = MESSAGGIO_CHECK.search(message.text)
		if match:
			text += "\n` → ` " + match["msg"]
		await client.send_message(CONFIG()["log"]["group"], text)
	
@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(pattern=r"Messaggio da"), group=70)
async def messaggio_diretto(client, message):
	if CONFIG()["log"]["pin"]["dm"]:
		await message.pin()

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.regex(
	pattern=r"Hai ricevuto|" +
			r"In mezzo ai mucchi trovi un Kit Fuga!|" +
			r"Le miniere sono state chiuse, hai ricevuto"
), group=70)
async def hai_ricevuto(client, message):
	if CONFIG()["log"]["pin"]["reward"]:
		await message.pin()
