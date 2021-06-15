import asyncio
import json
import time
import sys
import ast
import io

import requests

from pyrogram import filters

from util.permission import is_superuser
from util.command import filterCommand
from util.message import ProgressChatAction, edit_or_reply
from util.decorators import report_error, set_offline, cancel_chat_action

from bot import alemiBot

import logging
logger = logging.getLogger(__name__)

from plugins.lootbot.common import CONFIG
from plugins.lootbot.loop import LOOP, StateDict

TASK_INTERRUPT = False

# Macro for night mode
@alemiBot.on_message(is_superuser & filterCommand(["lnight", "lnt"], list(alemiBot.prefixes)))
@report_error(logger)
@set_offline
async def toggle_night(client, message):
	cfg = CONFIG.get()
	if type(cfg["night"]) is not bool:
		cfg["night"] = False
	cfg["night"] = not cfg["night"]
	CONFIG.update(cfg)
	await CONFIG.serialize()
	await edit_or_reply(message, f"` → ` Night mode [`{'ON' if cfg['night'] else 'OFF'}`]")

@alemiBot.on_message(is_superuser & filterCommand(["lfriend", "lfriends"], list(alemiBot.prefixes)))
@report_error(logger)
@set_offline
async def sync_friends_command(client, message):
	out = ""
	cfg = CONFIG.get()
	if len(message.command.arg) > 0:
		cfg["sync"]["friends"]["url"] = message.command.arg[0]
		CONFIG.update(cfg)
		await CONFIG.serialize()
		out += f"` → lb.sync.friends.url` : --{message.command.arg[0]}--\n" 
	data = requests.get(cfg["sync"]["friends"]["url"]).json()
	with open("plugins/lootbot/data/friends.json", "w") as f:
		json.dump(data, f)
	LOOP.state["friends"] = data
	out += f"` → ` Synched {len(data)} friends\n"
	await edit_or_reply(message, out)

def format_recursive(layer, level, base=""):
	if type(layer) is not dict and type(layer) is not StateDict:
		return str(layer) + "\n"
	out = "\n"
	view = list(layer.keys())
	last = False
	for key in view:
		last = key == view[-1]
		out += base + ('├' if not last else '└') + f" `{key}` : " + \
					format_recursive(layer[key], level+1, base+("　\t" if last else "│\t"))
	return out

def extract(data, text):
	keys = list(text.split("."))
	val = data
	for k in keys:
		if k in val:
			val = val[k]
		else:
			return None
	return val

@alemiBot.on_message(is_superuser & filterCommand(["lvar", "lvars"], list(alemiBot.prefixes)))
@report_error(logger)
@set_offline
@cancel_chat_action
async def get_loopstate(client, message):
	if len(message.command) > 0:
		state = extract(LOOP.state, message.command[0])
		text = f"lstate.{message.command[0]}"
		out = f"`{text} → `" + format_recursive(state, 0)
		await edit_or_reply(message, out)
	else:
		await edit_or_reply(message, "` → ` Sending loop state")
		prog = ProgressChatAction(client, message.chat.id)
		out = io.BytesIO((str(LOOP.state)).encode('utf-8'))
		out.name = f"loop-state.json"
		await client.send_document(message.chat.id, out, progress=prog.tick)

@alemiBot.on_message(is_superuser & filterCommand(["lconfig", "lcfg"], list(alemiBot.prefixes)))
@report_error(logger)
@set_offline
async def get_config(client, message):
	cfg = CONFIG
	text = "lcfg"
	if len(message.command) > 0:
		cfg = extract(cfg, message.command[0])
		text = f"lcfg.{message.command[0]}"
	out = f"`{text} → `" + format_recursive(cfg, 0)
	await edit_or_reply(message, out)

@alemiBot.on_message(is_superuser & filterCommand(["lset"], list(alemiBot.prefixes), flags=["-f", "-state"]))
@report_error(logger)
@set_offline
async def set_config(client, message):
	if len(message.command) < 1:
		return
	edit_state = bool(message.command["-state"])
	data = LOOP.state if edit_state else CONFIG.get()
	s = message.command[0].split(".")
	force = message.command["-f"]
	key = s.pop(-1)
	pre = s
	if len(message.command) > 1:
		val = message.command[1]
	else:
		return await edit_or_reply(message, "`[!] → ` No value given")
	if val.lower() in ["true", "t"]:
		val = True
	elif val.lower() in ["false", "f"]:
		val = False
	else:
		try:
			val = ast.literal_eval(val)
		except:
			pass
	logger.info(f"Setting \'{'.'.join(pre)}.{key}\' to {val}")
	curr = data
	for k in pre:
		if k not in curr:
			return await edit_or_reply(message, f"`[!] → ` No such setting")
		curr = curr[k]
	if key not in curr:
		return await edit_or_reply(message, f"`[!] → ` No such setting (**{key}**)")
	if not force:
		if type(curr[key]) is dict:
			return await edit_or_reply(message, f"`[!] → ` **{key}** is a category")
		if type(curr[key]) != type(val):
			return await edit_or_reply(message, f"`[!] → ` Wrong type (`{type(val).__name__}`, expected `{type(curr[key]).__name__}`)")
		if type(val) is list and len(val) != len(curr[key]):
			return await edit_or_reply(message, f"`[!] → ` Not enough elements (**{len(val)}**, expected **{len(curr[key])}**)")
	curr[key] = val
	if not edit_state:
		CONFIG.update(data)
		await CONFIG.serialize()
	await edit_or_reply(message, f"` → ` {'**[F]**' if force else ''} `{'.'.join(pre)}.{key}` : --{val}--")

@alemiBot.on_message(is_superuser & filterCommand(["ltask", "task", "tasks"], list(alemiBot.prefixes), options={
	"updates" : ["-u", "-upd"],
	"interval" : ["-i", "-int"]
}, flags=["-stop"]))
@report_error(logger)
@set_offline
async def get_tasks(client, message):
	global TASK_INTERRUPT
	if message.command["-stop"]:
		TASK_INTERRUPT = True
		return
	times = int(message.command["updates"] or 3)
	interval = float(message.command["interval"] or 5)
	last = ""
	for _ in range(times):
		out = f"`→ ` --{LOOP.current.ctx.name if LOOP.current is not None else 'N/A'}--\n"
		for task in LOOP.tasks:
			out += f"` → ` {task.ctx.name}\n"
		if out != last:
			await edit_or_reply(message, out)
			last = out
		await asyncio.sleep(interval)
		if TASK_INTERRUPT:
			break
	await edit_or_reply(message, f"`→ ` {'Stopped' if TASK_INTERRUPT else 'Done'}")
	TASK_INTERRUPT = False
