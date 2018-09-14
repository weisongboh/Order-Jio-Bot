# Supperbot implementation using telepot wrapper

import time as ostime
from datetime import *
import pandas as pd
from myconfig import * # Change myconfig to your config file
import telepot
from telepot.loop import *
from telepot.namedtuple import *
from telepot.delegate import pave_event_space, per_chat_id, create_open
import threading as thr
from collections import OrderedDict

bot = telepot.Bot(bot_token)
print(bot.getMe())
bot_name = '@' + bot.getMe()['username']
print(bot_name)

order_pad = OrderedDict() #structure -> user_id: [orderlist1, orderlist2,...]
order_master_list = OrderedDict() #Structure -> inline_message_id: orderlist
user_state = {} # Tracks if bot is awaiting response from user. [True/False, msg_id to get, type, inline_message_id, origin_id]

# Shared keyboards/button list
grp_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                   [InlineKeyboardButton(text='Join Order', callback_data='join_order'),
                   InlineKeyboardButton(text='Update', callback_data='grp_update')],
               ])

admin_shared_buttons = [
                   [InlineKeyboardButton(text='Add Order', callback_data='add_order'),
                    InlineKeyboardButton(text='Delete Order', callback_data='del_order'),
                    InlineKeyboardButton(text='Update', callback_data='admin_update')],
                   [InlineKeyboardButton(text='Lock orderlist', callback_data='lock_order'),
                    InlineKeyboardButton(text='Unlock orderlist', callback_data='unlock_order')],
                   ]


# Orderlist class

class Orderlist():
    def __init__(self, title, admin_id):
        self.title = title
        self.admin_id = (admin_id, None) #(admin_user_id, master_list_id)
        self.edit_id = None # inline_message_id
        self.order = OrderedDict() # structure -> name: order
        self.lock = False #state of orderlist, True = locked, False = unlocked
        self.keyboard = InlineKeyboardMarkup(inline_keyboard=[
                   [InlineKeyboardButton(text='Add Order', callback_data='add_order'),
                    InlineKeyboardButton(text='Delete Order', callback_data='del_order')],
                   [InlineKeyboardButton(text='Update', callback_data='update')],
                   ])

    def get_title(self):
        return self.title
    
    def get_chat_id(self):
        return self.edit_id[0]

    def get_admin_id(self):
        return self.admin_id
    
    def get_edit_id(self):
        return self.edit_id

    def get_keyboard(self):
        return self.keyboard

    def get_orders(self):
        return self.order

    def get_lock_status(self):
        return self.lock

    def get_user_order(self, username):
        user_order = self.get_orders()[username]
        return user_order
    
    #Methods
    def add_order(self,name, text):
        order_list = self.get_orders()
        if name in order_list:
            print('order entry exist', name, text)
            return False
        else:
            order_list[name] = text
            return True
        
    def del_order(self, name):
        if name in self.order:
            del self.order[name]
            print(self.order)
            return True

    def publish_order(self):
        result_text = self.title + '\n'
        for user in self.order:
            result_text += (user + ' - '+ self.order[user] + '\n')
        
        return result_text
    
    
# Methods called by commands

def start(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    instructions = 'Welcome to OrderJioBot!\n\nCollate orders easily using this bot.'\
                '\nYou can only join one orderlist at a time.\n/new to start new order'
    bot.sendMessage(chat_id, instructions)

def neworder(msg):
    content_type, chat_type, chat_id = telepot.glance(msg) #chat id = grp id if made in group.
    user_id = msg['from']['id']
    
    title_req = bot.sendMessage(user_id, 'Please send me the title of your Order list')
    title_user_id, title_text_id = telepot.message_identifier(title_req)
    user_state[user_id] = [True, title_text_id + 1, 'title', None, None] #Set bot to take next reply as input
    
   
def order_input(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    username = get_username(msg)
    user_id = msg['from']['id']
    state, text_id, text_type, inline_message_id, origin_id = user_state[chat_id]

    if text_type == 'title':
        title = msg['text']
        new_order = Orderlist(title, user_id) # Creates an instance of Orderlist
        order_text = new_order.publish_order()

        user_state[chat_id] = [False, None, None, inline_message_id]
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=admin_shared_buttons+
                   [[InlineKeyboardButton(text='Publish', switch_inline_query=title)]])
        
        message = bot.sendMessage(chat_id, order_text, reply_markup=admin_keyboard) #sends message to chat
        admin_tup = telepot.message_identifier(message)
        new_order.admin_id = admin_tup

        if user_id in order_pad:
            order_pad[user_id][admin_tup[1]] = new_order
        else:
            order_pad[user_id]= OrderedDict()
            order_pad[user_id][admin_tup[1]] = new_order
            
        bot.sendMessage(chat_id, 'You can now share the order list to collate orders')
        return True
    
    if inline_message_id == None: # When admin wants to add order and no one has added yet.
        chosen_orderlist = order_pad[origin_id[0]][origin_id[1]] #Retrieves the target orderlist
    else:
        chosen_orderlist = order_master_list[inline_message_id] #Retrieves the target orderlist
        
    if text_type == 'add_order':
        user_order = msg['text']
        chosen_orderlist.add_order(username, user_order)
        bot.sendMessage(chat_id, ('Your order has been added:\n'+user_order))
        user_state[chat_id] = [False, None, None, inline_message_id, origin_id]
            
def about(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    abt_text = 'OrderJioBot made by Wei Song using telepot wrapper\n'\
                'Do report any bugs found.'
    bot.sendMessage(chat_id, abt_text)
        
        
cmd_handler = {'/start': start,
               '/new': neworder,
               '/about': about
            }
# Command processing
def get_command_arg(msg):
    #checks if command is followed by an argument, returns argument in string. 
    text_len = len(msg['text']) #length of text message
    comm_len = get_command_length(msg) #length of command
    if text_len > get_command_length(msg):
        arg = msg['text'][comm_len+1:]
    else:
        arg = False
    return arg

def msg_type(msg):
    #returns type of entities contained in message, in string
    
    if 'entities' in msg:
        msg_type = msg['entities'][0]['type']
    else:
        msg_type = list(msg)[4]
        
    return msg_type

def on_command(msg):
    print('Command Received')
    command_length = msg['entities'][0]['length']
    command = msg['text']
    if bot_name in command: #removes bot @handle from command if it exist
        command = command.replace(bot_name, '')
    cmd_handler[command[:command_length]](msg)
    
def get_username(msg):
    return msg['from']['first_name']


# Message flavour processing

def on_chat_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)

    if msg['from']['is_bot']: #ignores messages sent by bot
        return True
    
    txt_type = msg_type(msg) # The following check message type and pass to appropriate handlers.
    
    if txt_type == 'bot_command':
        on_command(msg)
        
    if txt_type == 'text':
        if chat_id in user_state:
            if user_state[chat_id][0]:
                order_input(msg)
        else:
            print('text received')
    
    if txt_type == 'photo':
        print('photo received')

def on_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    msg_update = telepot.origin_identifier(msg)
    username = get_username(msg)
    
    if 'inline_message_id' in msg:
        inline_message_id = msg['inline_message_id']
    else:
        inline_message_id = user_state[from_id][3]
        
    if inline_message_id == None: # When admin wants to add order and no one has added yet.
        origin_user, origin_msg_id = msg_update
        retrieved_order = order_pad[origin_user][origin_msg_id] #Retrieves the target orderlist
    else:
        retrieved_order = order_master_list[inline_message_id] #Retrieves the target orderlist
    
    title = retrieved_order.get_title()
    
    if query_data == 'add_order':
        
        if retrieved_order.get_lock_status():
            bot.sendMessage(from_id, 'The orderlist is locked')
            bot.answerCallbackQuery(query_id, text='Order locked!')
        elif username in retrieved_order.get_orders():
            bot.sendMessage(from_id, 'Order exist! Delete order and then place a new order' )
            bot.answerCallbackQuery(query_id, text='Order Exist')
        else:
            order_req = bot.sendMessage(from_id, 'Adding order, what is your order?')
            order_user_id, order_text_id = telepot.message_identifier(order_req)
            user_state[from_id] = [True, order_text_id+1, 'add_order', inline_message_id, retrieved_order.get_admin_id()] #set bot to take next input from user as order
            bot.answerCallbackQuery(query_id, text='Adding order')
            
    if query_data == 'del_order':
        if retrieved_order.get_lock_status():
            bot.sendMessage(from_id, 'The orderlist is locked')
            bot.answerCallbackQuery(query_id, text='Order locked!')
        elif username in retrieved_order.get_orders():
            previous_order = retrieved_order.get_user_order(username)
            retrieved_order.del_order(username)
            bot.sendMessage(from_id, ('Your previous order has been deleted:\n'+previous_order))
            bot.answerCallbackQuery(query_id, text='Order deleted')
        else:
            bot.sendMessage(from_id, 'No order has been placed' )
            bot.answerCallbackQuery(query_id, text='Please place order')
    
    if query_data == 'join_order':
        bot.sendMessage(from_id, ('Joining order: '+ title), reply_markup=retrieved_order.get_keyboard())
        user_state[from_id] = [False, None, None, inline_message_id]
        bot.answerCallbackQuery(query_id, text='PM sent, check OrderJioBot chat')

    if query_data == 'update':
        try:
            bot.editMessageText(msg_update, retrieved_order.publish_order(), reply_markup=retrieved_order.get_keyboard())
        except:
            pass
        bot.answerCallbackQuery(query_id, text='Orderlist updated!')
        
    if query_data == 'grp_update':
        try:
            bot.editMessageText(msg_update, retrieved_order.publish_order(), reply_markup=grp_keyboard)
        except:
            pass
        bot.answerCallbackQuery(query_id, text='Orderlist updated!')

    if query_data == 'admin_update':
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=admin_shared_buttons+
                   [[InlineKeyboardButton(text='Publish', switch_inline_query=title)]])
        try:
            bot.editMessageText(msg_update, retrieved_order.publish_order(), reply_markup=admin_keyboard)
        except:
            pass
        bot.answerCallbackQuery(query_id, text='Orderlist updated!')
        
    if query_data == 'lock_order':
        retrieved_order.lock = True
        bot.answerCallbackQuery(query_id, text='Order has been locked')
    
    if query_data == 'unlock_order':
        retrieved_order.lock = False
        bot.answerCallbackQuery(query_id, text='Order has been unlocked')
        
def on_inline_query(msg):
    query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
    print ('Inline Query:', query_id, from_id, query_string)
    
    user_order_pad = order_pad[from_id]
    inline_articles = []
    for order_id in user_order_pad:
        order_list = user_order_pad[order_id]
        order_title = order_list.get_title()
        order_text = order_list.publish_order()
        inline_articles.append(InlineQueryResultArticle(id=order_id,
                                                        title=order_title,
                                                        input_message_content=InputTextMessageContent(
                                                            message_text=order_text),
                                                        reply_markup=grp_keyboard
                                                        )
                               )

    bot.answerInlineQuery(query_id, inline_articles)

def on_chosen_inline_result(msg):
    result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
    inline_message_id = msg['inline_message_id']
    chosen_orderlist = order_pad[from_id][int(result_id)] # Retrieve Chosen order list
    chosen_orderlist.edit_id = inline_message_id #sets edit id for future edits
    order_master_list[inline_message_id] = chosen_orderlist
    
    print ('Chosen Inline Result:', result_id, from_id, query_string, inline_message_id)

## Starts listening for messages
MessageLoop(bot, {'chat': on_chat_message,
                  'callback_query': on_callback_query,
                  'inline_query': on_inline_query,
                  'chosen_inline_result': on_chosen_inline_result}
            ).run_as_thread()

print('Listening ...')

def debug():
    print('\norder_pad\n', order_pad)
    print('\norder_master_list\n',order_master_list)
    print('\nuser_state\n',user_state)
    

