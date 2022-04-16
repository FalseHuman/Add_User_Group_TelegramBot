import telebot
from telebot import types
import telethon
from telethon import TelegramClient, sync
from telethon.tl.functions.messages import ImportChatInviteRequest
import sqlite3, time, logging, asyncio, requests

logging.basicConfig(format='%(asctime)s %(levelname)s - %(message)s',
                    level=logging.INFO, filename='bot.log')

token = 'YOUR_TOKEN'

bot = telebot.TeleBot(str(token))

owner = 'YOUR_ID_TELEGRAM'


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn = types.KeyboardButton('Зарегистрироватьcя')
    btn2 = types.KeyboardButton('Посмотреть список пользователей')
    btn3 = types.KeyboardButton('Посмотреть список групп')
    connect = sqlite3.connect('group.db')
    cursor = connect.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS user_manager(
        id INTEGER,
        api_id INTEGER,
        name TEXT,
        api_hash TEXT,
        phone INTEGER,
        phone_code_hash TEXT
    )""")
    connect.commit()
    user_id = message.chat.id
    cursor.execute(f"SELECT id FROM user_manager WHERE id = {user_id}")
    data = cursor.fetchone()
    if data is None:
        cursor.execute(f"INSERT INTO user_manager VALUES(?, ?, ?, ?, ?, ?);",
                       (user_id, user_id, message.from_user.first_name, user_id, user_id, user_id))
        connect.commit()
        if message.chat.id == owner:
            markup.add(btn2)
            markup.add(btn3)
            send_message = f"<b>Привет {message.from_user.first_name}!</b>\ Для того чтобы воспользоваться ботом нажми /instruction"
            bot.send_message(message.chat.id, send_message,
                             parse_mode='html', reply_markup=markup)
        else:
            markup.add(btn)
            send_message = f"<b>Привет {message.from_user.first_name}!</b>\nДля того чтобы воспользоваться ботом нажми /instruction"
            bot.send_message(message.chat.id, send_message,
                             parse_mode='html', reply_markup=markup)
    else:
        if message.chat.id == owner:
            markup.add(btn3)
            markup.add(btn2)
        else:
            markup.add(btn)
        bot.send_message(message.chat.id, f'Мы Вас помним:) Для того чтобы воспользоваться ботом нажми /instruction',
                         parse_mode='html', reply_markup=markup)


@bot.message_handler(regexp="^\d+$")
def get_id(message):
    id_ = message.text[1:]        # as string without `/`
    # id_ = int(message.text[1:])  # as integer
    bot.send_message(message.chat.id, f'{id_}')


@bot.message_handler(commands=['instruction'])
def messages(message):

    if message.chat.id == owner:
        user_owner = """<b>Инструкция:</b>\nДля того чтобы посмотреть список пользователей нажми Посмотреть список пользователей\nДля того чтобы посмотреть список групп - Посмотреть список групп\nДля того чтобы добавить группу нажми - /add_group\nЧтобы добавить пользователей в группы нажми -/group_user_add"""
        bot.send_message(message.chat.id, user_owner, parse_mode='html')
    else:
        no_owner = """<b>Инструкция:</b>\nДля того чтобы зарегистрироваться нажми кнопку Зарегистрироваться, предварительно нужно зарегистрировать приложение тут - Заходим в пункт "API". Ищем "Telegram API" и заходим в "Creating an application" (https://my.telegram.org/apps).\nДля того чтобы подключиться /connect (P.S. после того как нажал кнопку Зарегистрироваться и ввел данные)"""
        bot.send_message(message.chat.id, no_owner, parse_mode='html')


@bot.message_handler(commands=['add_group'])
def messages(message):
    connect = sqlite3.connect('group.db')
    cursor = connect.cursor()
    final_message = 'Введите данные через запятую в таком формате: Группа: название группы, ссылка на группу'
    cursor.execute("""CREATE TABLE IF NOT EXISTS group_link(
        id INTEGER PRIMARY KEY,
        namegroup TEXT,
        linkgroup TEXT
    )""")
    connect.commit()
    bot.send_message(message.chat.id, final_message, parse_mode='html')


@bot.message_handler(commands=['group_user_add'])
def messages(message):
    connect = sqlite3.connect('group.db')
    cursor = connect.cursor()
    cursor.execute(f"SELECT id, api_id, api_hash FROM user_manager")
    data = cursor.fetchall()
    for user in data:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            client = TelegramClient(
                f'{user[0]}', user[1], user[2], loop=loop)
            client.connect()
            cursor.execute(f"SELECT linkgroup FROM group_link")
            group = cursor.fetchall()
            for link in group:
                if 'joinchat' in link:
                    link = link[0].replace("https://t.me/joinchat/", "")
                else:
                    link = link[0].replace("https://t.me/+", "")
                try:
                    if client.is_user_authorized():
                        client(ImportChatInviteRequest(link))
                        time.sleep(3)
                except Exception as e:
                    pass
            client.disconnect()
        except Exception as e:
            url = "https://api.telegram.org/bot" + token
            chat_id=f'{user[0]}'
            method = url + "/sendMessage"
            text = 'Была произведена попытка добавления Вас в список групп, но вы не авторизованы в приложении. Пожалуйста авторизуйтесь и попросите добавить Вас ещё раз!'
            r = requests.post(method, data={"chat_id": chat_id, "text": text})
    final_message = 'Был произведен процесс добавления пользователей в группы'
    bot.send_message(message.chat.id, final_message, parse_mode='html')


@bot.message_handler(commands=['connect'])
def messages(message):
    connect = sqlite3.connect('group.db')
    cursor = connect.cursor()
    cursor.execute(
        f"SELECT id, api_id, api_hash, phone FROM user_manager WHERE id = {message.chat.id}")
    data = cursor.fetchone()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(data)
    client = TelegramClient(f'{message.chat.id}',
                            data[1], data[2].strip(), loop=loop)
    client.connect()
    if not client.is_user_authorized():
        try:
            client.send_code_request(data[3])
            phone_code_hash = client.send_code_request(data[3]).phone_code_hash
            sql_update_query = F"UPDATE user_manager SET phone_code_hash=? WHERE id = ?"
            data = (phone_code_hash, message.chat.id)
            cursor.execute(sql_update_query, data)
            connect.commit()
            bot.send_message(
                message.chat.id, f'Успешное подключение! Введите код в таком формате - Код: цифры кода')
        except Exception as e:
            bot.send_message(message.chat.id, f'Ошибка подключения: {e}')
    else:
        bot.send_message(message.chat.id, f'Вы уже подключены')
    client.disconnect()


@bot.message_handler(content_types=['text'])
def mess(message):
    connect = sqlite3.connect('group.db')
    cursor = connect.cursor()
    user_id = message.chat.id
    get_message_bot = message.text
    cursor.execute(
        f"SELECT id, api_id, api_hash, phone, phone_code_hash FROM user_manager WHERE id = {message.chat.id}")
    data = cursor.fetchone()
    if get_message_bot == 'Посмотреть список пользователей' and message.chat.id == owner:
        cursor.execute(f"SELECT * FROM user_manager")
        data = cursor.fetchall()
        message_all_user = 'Все пользователи: \n'
        for user in data:
            message_all_user += f'Менеджер: {user[2]} - Удалить: /delete_{str(user[0])}\n------\n'
        bot.send_message(message.chat.id, message_all_user, parse_mode='html')
    elif get_message_bot == 'Посмотреть список групп' and message.chat.id == owner:
        cursor.execute(f"SELECT * FROM group_link")
        data = cursor.fetchall()
        message_all_user = 'Список групп: \n'
        for user in data:
            message_all_user += f'Название группы: {user[1]}\nСсылка: {user[2]}\nУдалить: /delete_group_{str(user[0])}\n------\n'
        bot.send_message(message.chat.id, message_all_user, parse_mode='html')
    elif '/delete_' in get_message_bot and 'group' not in get_message_bot and message.chat.id == owner:
        user_id = get_message_bot.replace("/delete_", "")
        cursor.execute(f"DELETE FROM user_manager WHERE id = {int(user_id)}")
        connect.commit()
        bot.send_message(
            message.chat.id, f"Пользователь с  id={user_id} удален!")
    elif '/delete_group_' in get_message_bot and message.chat.id == owner:
        user_id = get_message_bot.replace("/delete_group_", "")
        cursor.execute(f"DELETE FROM group_link WHERE id = {int(user_id)}")
        connect.commit()
        bot.send_message(message.chat.id, f"Группа с  id={user_id} удален!")
    elif ',' not in get_message_bot and "Код" not in get_message_bot and 'Группа' not in get_message_bot:
        bot.send_message(
            message.chat.id, f'Введите данные через запятую в таком формате: api_id, api_hash, номер телефона')
    elif ',' in get_message_bot and "Код" not in get_message_bot and 'Группа' not in get_message_bot:
        message_auth = get_message_bot.split(',')
        sql_update_query = F"UPDATE user_manager SET api_id = ?, api_hash=?, phone=? WHERE id = ?"
        data = (message_auth[0], message_auth[1], message_auth[2], user_id)
        print(data)
        cursor.execute(sql_update_query, data)
        connect.commit()
        bot.send_message(
            message.chat.id, f'Вы ввели сообщение {get_message_bot}. Если хотите исправить, то нажмите кнопку регистрации заново. Для того чтобы подключить приложение нажмите /connect')
    elif "Код" in get_message_bot:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TelegramClient(
            f'{message.chat.id}', data[1], data[2].strip(), loop=loop)
        client.connect()
        get_message_bot = get_message_bot.replace("Код:", '')
        if not client.is_user_authorized():
            try:
                client.sign_in(data[3], int(get_message_bot),
                               phone_code_hash=data[4])
                bot.send_message(message.chat.id, f'Успешное подключение!')
            except Exception as e:
                print(int(get_message_bot))
                bot.send_message(message.chat.id, f'Ошибка подключения: {e} ')
        else:
            bot.send_message(message.chat.id, f'Вы уже подключены')
        client.disconnect()
    elif 'Группа' in get_message_bot and '/add_group' not in get_message_bot:
        get_message_bot = get_message_bot.replace('Группа:', '')
        get_message_bot = get_message_bot.split(',')
        data = (get_message_bot[0].strip(), get_message_bot[1].strip())
        cursor.execute(f"INSERT INTO group_link VALUES(NULL, ?, ?);", data)
        connect.commit()
        bot.send_message(message.chat.id, "Данные добавил!")


while True:
    try:
        bot.polling(none_stop=True)  # Это нужно чтобы бот работал всё время
    except:
        time.sleep(5)  # если ошибка бот уходит в спящий режим на 5 секунд
