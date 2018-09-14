import time as ostime
from datetime import *
import pandas as pd
from myconfig import *
from telegram.ext import *
import telegram
import logging
import threading as thr

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

#Telegram supper bot
bot = telegram.Bot(bot_token)
print(bot.getMe())

def start(bot, update):
    # Sends a message when command /start is issued
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")

def telehelp(bot, update):
    # Sends a message when command /help is issued
    pass

def error(bot, update, error):
    #Log Errors caused by Updates
    logger.warning('Update "%s" caused error "%s"', update, error)
    
def echo(bot, update):
    pass

def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(bot_token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", telehelp))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


        
if __name__ == '__main__': # If this module is being imported, code below will not run
    main()
