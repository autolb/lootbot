# lootbotplugin
Questo e' un plugin per il mio userbot, ([alemibot](https://github.com/alemigliardi/alemibot)), per automatizzare @lootgamebot. Non è barare, la conoscienza è potere! 😎

## Features
* Auto Dungeon (molto configurabile, fa imprese auto)
* Auto Mappe (molto configurabile, anche R4 1000 ti porta in Top 20 garantito)
* Auto Incarichi (sceglie auto)
* Auto Assalto (incrementa auto)
* Auto Missioni (gemma sopra rarita', fa imprese auto)
* Auto Cave/Esplorazioni (gemma, ritorna finche' non dimezzata, fa imprese auto)
* Auto Ispezioni (manda gnomo, gemma, gioca il gioco delle rune, fa imprese auto)
* Auto Contrabbandiere (crafta e vende da solo)
* Auto Scrigni (compra tutti quelli disponibili)
* Auto Eventi
	* Generatore di Polvere (avvia, ritira auto)
	* Miniera di Mana (avvia)
	* Ricercato (auto)
	* Itinerario Propizio (auto)
	* Pupazzi di Neve (lancia palle di neve auto)
* Auto random checks (cariche esplorative, polvere, mana, ...)

# Installazione
## Heroku
Heroku e' una piattaforma che affitta a developers e aziende piccoli containers (docker) per eseguire applicazioni : i dynos.
Heroku offre dyno con forti limiti gratis, ma per eseguire un bot di telegram le poche risorse offerte sono comunque sufficienti.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/alemidev/alemibot/tree/heroku&env[PLUGINS]=autolb/lootbot)

Usa questo [link](https://replit.com/@dashezup/generate-pyrogram-session-string) per generare una sessione.
Dovrai inserire API\_ID e API\_HASH (puoi cercarne di default o recuperare i tuoi su [my.telegram.org](https://my.telegram.org/)) e il tuo numero di telefono, 
e riportare il codice che ricevi. (Il sito e' `repl`, che esegue frammenti di codice in sandox online. 
Puoi controllare il codice che sta venendo eseguito sulla scheda "Code". E' uno script minimo con l'unico scopo di generarti una stringa di sessione)

Inserisci quindi la stringa che hai ottenuto nei salvati, API\_ID e API\_HASH nei campi sulla pagina di Heroku e premi "deploy"

Una volta finito di creare l'app, dovrai attivarla: vai su "Manage app", poi sulla tab "Resources" modifica lo stato dell'unico 
worker da spento ad acceso (la spunta, prima il tasto 'modifica' viola)

Il tuo bot e' pronto e partito! Nei tuoi messaggi salvati, controlla il tuo config con `/lcfg [<sub>]` e cambia i parametri che vuoi con `/lset <param> <value>`

Heroku riavvia il tuo dyno ogni 24h, resettanto percio' il tuo config. (stiamo reworkando il caricamento del config per evitare questo, stay tuned)
## Manuale
E' necessario prima di tutto installare [alemibot](https://github.com/alemigliardi/alemibot), segui la guida per installare `alemibot`.

Una volta correttamente installato, sara' sufficiente scrivere (da telegram)
	`.install alemidev/lootbot`
E questo plugin verra' scaricato e installato automaticamente.

### Supporto
Scrivi in privato a [@alunduyn](https://t.me/alunduyn)! (anche chat segrete)

Il tuo interesse per questo progetto sara' tenuto assolutamente segreto: le nostre chat non saranno divulgate e non ti mettero' in contatto con altri utilizzatori **se non su tua e loro richiesta**.

Non ti fidi? Ti garantisco che non sono l'unico ad usare questo plugin! L'unico motivo per cui edo mi ha bannato e' perche' gli ho mandato io un link a questo repo (:

# Utilizzo

Appena installato, tutte le attivita' saranno disattivate.
Usa `.lcfg` per mostrare tutte le opzioni disponibili
Usa `.lset` per modificare il tuo config

## Comandi

I comandi di questo plugin **non appaiono sulla pagina di aiuto di alemibot** (per ovvi motivi di riservatezza).
I comandi aggiunti da questo plugin sono comunque pochi e per lo piu` relativi al config file:

* Usa `.lset <setting> <value>` per modificare un opzione. Separa sotto-opzioni con `.` : `.lset dungeon.auto true`
* Usa `.lcfg` per mostrare il tuo config. Puoi specificare una categoria da mostrare : `.lcfg` o `.lcfg dungeon`
* Usa `.lcraft <item>` per avviare un craft automatico: per prima cosa sincronizzera' l'inventario con @craftlootbot, poi richiedera' la lista di craft e infine iniziera' il craft loop
	* Aggiungi la flag `-stop` per interrompere un craft in corso
	* Aggiungi la flag `-sync` per sincronizzare solamente l'inventario con CLB
	* Aggiungi la flag `-craft` per richiedere subito una lista di craft senza prima sincronizzare l'inventario
* Usa `.lchest` per comprare automaticamente piu` scrigni che puoi
* Usa `.lmap` per mostrare le caselle esplorate sulla mappa in corso
* Usa `.lvar` per mostrare tutte le variabili di stato (debug)