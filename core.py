import asyncio
import aiohttp
import logging
import json
import ast
import io

from typing import Optional, Any

from pyrogram import filters

from alemibot import alemiBot
from alemibot.util import sudo, filterCommand, ProgressChatAction, edit_or_reply, report_error, set_offline, cancel_chat_action

from .common import CONFIG
from .loop import LOOP, StateDict

TASK_INTERRUPT = False
logger = logging.getLogger(__name__)

# Macro for night mode
@alemiBot.on_message(sudo & filterCommand(["lnight", "lnt"]))
@report_error(logger)
@set_offline
async def toggle_night(client, message):
	if type(CONFIG()["night"]) is not bool:
		CONFIG()["night"] = False
	CONFIG()["night"] = not CONFIG()["night"]
	await CONFIG.serialize()
	await edit_or_reply(message, f"` → ` Night mode [`{'ON' if CONFIG()['night'] else 'OFF'}`]")

@alemiBot.on_message(sudo & filterCommand(["lfriend", "lfriends"]))
@report_error(logger)
@set_offline
async def sync_friends_command(client, message):
	out = ""
	if len(message.command.arg) > 0:
		CONFIG()["sync"]["friends"]["url"] = message.command.arg[0]
		await CONFIG.serialize()
		out += f"` → lb.sync.friends.url` : --{message.command.arg[0]}--\n" 
	async with aiohttp.ClientSession() as sess:
		async with sess.get(CONFIG()["sync"]["friends"]["url"]) as res:
			data = await res.json()
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

def _extract(data:dict, query:str) -> Optional[Any]:
	keys = list(query.split("."))
	for k in keys:
		if k in data:
			data = data[k]
		else:
			return None
	return data

@alemiBot.on_message(sudo & filterCommand(["lvar", "lvars"]))
@report_error(logger)
@set_offline
@cancel_chat_action
async def get_loopstate(client, message):
	if len(message.command) > 0:
		state = _extract(LOOP.state, message.command[0])
		text = f"lstate.{message.command[0]}"
		out = f"`{text} → `" + format_recursive(state, 0)
		await edit_or_reply(message, out)
	else:
		await edit_or_reply(message, "` → ` Sending loop state")
		prog = ProgressChatAction(client, message.chat.id)
		out = io.BytesIO((str(LOOP.state)).encode('utf-8'))
		out.name = f"loop-state.json"
		await client.send_document(message.chat.id, out, progress=prog.tick)

def _parse_val(val:str) -> Any:
	if val.lower() in ["true", "t"]:
		return True
	if val.lower() in ["false", "f"]:
		return False
	try:
		return ast.literal_eval(val)
	except Exception:
		return val

@alemiBot.on_message(sudo & filterCommand(["lcfg", "lconfig", "lset"], flags=["-f", "-state"]))
@report_error(logger)
@set_offline
async def get_config(client, message):
	edit_state = bool(message.command["-state"])
	data = LOOP.state if edit_state else CONFIG()
	if len(message.command) > 1:
		force = bool(message.command["-f"])
		keys = list(message.command[0].split("."))
		value = _parse_val(message.command[1])
		last = keys.pop()
		if len(keys) > 0:
			data = _extract(data, '.'.join(keys))
		# Some lame safety checks for users
		if not data:
			raise KeyError(f"No setting matching '{message.command[0]}'")
		if not force and type(data[last]) is dict:
			raise KeyError(f"Trying to replace category '{last}'")
		if not force and type(data[last]) is not type(value):
			raise ValueError(f"Wrong type: expected {type(data[last]).__name__} but got {type(value).__name__}")
		if not force and type(data[last]) is list and len(data[last]) != len(value):
			raise ValueError(f"Wrong length: expected {len(data[last])} values, got {len(value)}")
		data[last] = value
		if not edit_state:
			await CONFIG.serialize()
		await edit_or_reply(message, f"` → ` {'**[F]**' if force else ''} `lcfg.{message.command[0]}` : --{value}--")
	else:
		text = "lcfg"
		if len(message.command) > 0:
			data = _extract(data, message.command[0])
			text = f"lcfg.{message.command[0]}"
		out = f"`{text} → `" + format_recursive(data, 0)
		await edit_or_reply(message, out)

@alemiBot.on_message(sudo & filterCommand(["ltask", "task", "tasks"], options={
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
