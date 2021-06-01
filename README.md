# lootbotplugin
This is a plugin for my userbot ([alemibot](https://github.com/alemigliardi/alemibot)) to automate @lootgamebot. This definitely is cheating.

## Installation

You should first set up [alemibot](https://github.com/alemigliardi/alemibot). Check that repo for installation steps.

Once alemibot is installed, just run (from telegram)
	`.install alemidev/lootbot`
And it will install this plugin and reboot.

## Usage

By default, all tasks are disabled.
Run `.lcfg` to see all available options.
Use `.lset` to enable tasks you want/need.

## Commands

There is no help for the commands as of now, but there really aren't many commands, most is auto or editing config.

* Use `.lset <setting> <value>` to change a setting. Divide subsettings with `.` : `.lset dungeon.auto true`
* Use `.lcfg` to get current config (defaults to all tasks `False`)
* Use `.lcraft <item>` to auto craft something. You can add flag `-stop` to stop ongoing craft. It will first sync then craft, you can do only one of the two with either `-sync` or `-craft`.
* Use `.lchest` to automatically buy as many chests as you can afford
* Use `.lvar` to get a dump of the bot state.
