import json
import asyncio
import functools

from collections import deque

import heapq

import logging

from typing import Any

from pyrogram.raw.functions.account import UpdateStatus

from .common import random_wait, CONFIG, LOOTBOT

logger = logging.getLogger(__name__)

"""
A priority Queue implementation using python's heapq
"""
class PriorityQueue: # TODO
	def __init__(self, items=[]):
		self.q = []

	def __len__(self):
		return len(self.q)

	def add(item, priority=0):
		pass

	def pop(self):
		return self.q.pop(0)

"""
This is an enormous convenience class. This won't raise KeyErrors but just return None.
It will also print nicely and convert any dict fed in to this type too. If a non existing key
is requested, an empty new StateDict will be added for that key, so that saving in sub-dictionaries
directly is allowed ( from an empty dict, you can do d['a']['b'] ). If a field exists as an empty
dict, it was requested before being set
"""
class StateDict(dict):
	def __contains__(self, item: Any) -> bool:
		return super().__contains__(item)

	def __getitem__(self, key: Any) -> Any:
		if key in self:
			return super().__getitem__(key)
		super().__setitem__(key, StateDict())
		return super().__getitem__(key)

	def __setitem__(self, key: Any, value : Any) -> None:
		if type(value) is dict:
			value = StateDict(value)
		super().__setitem__(key, value)

	def __str__(self) -> str:
		return json.dumps(self, indent=2, ensure_ascii=False, default=str)

"""
This is the main task loop. It consist of a deque of coroutines.
The task loop starts empty and stopped. Any task that gets added, checks 
if the task loop is running; if not, a new task is started in the event loop.
This task will pop from the top of the deque tasks and run them. Once it's done,
it will terminate and mark itself as dead. Tasks added while the loop is running
will be added in queue but not start another loop. Tasks can be added to the front
of the queue.
"""
class TaskLoop(object):
	running = False
	active = True
	current = None
	tasks = deque()
	state = StateDict()

	def __len__(self):
		return len(self.tasks) + (1 if self.current else 0)

	def clear(self):
		self.tasks.clear()

	def cancel(self, name): # this is kinda ugly but for now will do
		for t in self.tasks:
			if t.ctx.name == name:
				self.tasks.remove(t)
				break

	def add_task(self, task, prio=False):
		if CONFIG()["night"]:
			logger.warning(f"[LB] Discarding task \'{task.ctx.name}\' due to Night Mode")
			return # prevent adding (and starting) tasks if in night mode
		task.ctx.state = self.state
		task.ctx.loop = self
		if prio:
			self.tasks.appendleft(task)
		else:
			self.tasks.append(task)
		if not self.running:
			self.start_loop()

	async def do_tasks(self):
		while len(self.tasks) > 0:
			try:
				await random_wait()
				self.current = self.tasks.popleft()
				await self.current()
			except:
				logger.exception(f"[LB] Exception raised in task \'{self.current.ctx.name}\'")
		self.running = False
		self.current = None

	def start_loop(self):
		self.running = True
		asyncio.get_event_loop().create_task(self.do_tasks())

LOOP = TaskLoop()

"""
The context object gets filled with the kwargs given in the decorator.
It prints itself nicely with json.dumps. Must be initialized with a name.
"""
class Context:
	def __init__(self, name):
		self.name = name
	def __str__(self):
		return json.dumps(self.__dict__, indent=2)
	def __getattr__(self, name:str) -> None: # Called only when accessing non-existing attributes
		return None

"""
This is the decorator to create a task object ready to be run by the TaskLoop.
Such tasks need to be manually added afterwards. A name needs to be given, and then
any number of kwargs can be specified, these will be added as attributes to the Context
object (ctx). ctx is received by your function, and thus it should have only ctx as attribute.
The resulting task can be called with no args, and will have a ctx attribute.
The task should be async, and can also be called on pre-existing functions like this:
	LOOP.add_task(create_task("name", client=client)(existing_func))
or directly to define tasks inside your handler:
	@create_task("name", client=client)
	async def mytask(ctx):
		print(ctx)
	LOOP.add_task(mytask)
"""
def create_task(name, **kwargs):
	ctx = Context(name)
	for k in kwargs:
		setattr(ctx, k, kwargs[k])
	def task_wrapper(func):
		@functools.wraps(func)
		async def task():
			logger.info(f"[LB] Running: {ctx.name}")
			return await func(ctx)
		task.ctx = ctx
		return task
	return task_wrapper
