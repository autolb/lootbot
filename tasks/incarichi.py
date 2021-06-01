import re

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup

from bot import alemiBot

from plugins.lootbot.common import LOOTBOT, LOOTPLUSBOT, random_wait, CONFIG
from plugins.lootbot.loop import LOOP, create_task

CFG = CONFIG["incarichi"]

CHOICES = ["In groppa al drago", "Uno sopra l'altro", "La ricerca di tanto cibo", "Un gruppo di Cerbrutti",
		   "Li attirate con un'esca", "Ne assaggiate per dimostrare la qualità", "Andate in Piazza",
		   "Cercate l'attrezzo", "Forzate la porta", "Lo affrontate", "Imbevuta nel veleno",
		   "Gli lanciate frecce", "Stanchi, vi trascinate verso la Taverna",
		   "Colpite la pazza in volto, vuole avvelenarvi!", "Quante armi. Non esercitarsi sarebbe da folli!",
		   "Non c'è scelta: proseguite.", "Abbatterete le porte a spallate, una ad una.",
		   "Mangiate il pasticcino. Senza alcun dubbio!",
		   "Ve ne andate, non volete avere a che fare con certaggente",
		   "Cercate riparo velocemente. Si salvi chi può!", "Accendete delle torce!",
		   "Vi avvicinate di soppiatto.",
		   "Vi presentate con le armi in pugno.", "Basta tergiversare: Dovete trovare il giardino!",
		   "Siete Guerrieri, ora basta!", "\"Che fame!\"", "Sembrerebbe un... Orso.", "Entrate e saccheggiate",
		   "Esplorate la grotta.", "Un piccolo ghigno nasce sulle vostre labbra...", "Li salutate.",
		   "Queste catene non sono nulla!", "Ragionate insieme, confrontando i ricordi",
		   "Portare i vostri omaggi agli spiriti degli avi: che vi proteggano!", "Decidete di imbarcarvi su Argo.",
		   "Vi radunate: serve un piano!",
		   "Entrate nel bosco in fila indiana, seguendo lui che oramai è eletto leader.",
		   "Decidete di accamparvi e recuperare le forze", "Decidete di attraversare cautamente uno alla volta.",
		   "Insieme lotterete contro il ciclope: sapete che il suo occhio è la sua debolezza.",
		   "Vi alzate e compattate in gruppo: Affronterete la cosa insieme.", "\"Aaaaaaaa!\"",
		   "Senza esitare rispondete in coro: \"Si, l'uomo!\"", "Sala da Pranzo", "La discarica", "Sono nascosti"]

@alemiBot.on_message(filters.chat(LOOTBOT) & filters.inline_keyboard, group=6969) # Do this for any message with inline buttons
async def auto_incarichi(client, message):
	if CFG["auto"]:
		kb = message.reply_markup.inline_keyboard
		for i in range(len(kb)):
			for j in range(len(kb[i])):
				if kb[i][j].text in CHOICES:
					await random_wait()
					await message.click(x=j, y=i)
					break

@alemiBot.on_message(filters.chat(LOOTPLUSBOT) & filters.regex(pattern=r"[^ ]+ ti incita a votare per l'incarico!"), group=6969)
async def incitato_a_votare(client, message):
	if CFG["auto"]:
		@create_task("Controlla incarico in corso", client=client)
		async def check_task(ctx):
			await ctx.client.send_message(LOOTBOT, "/incarico")
		LOOP.add_task(check_task)
