import telebot
from telebot import types
import telethon
from telethon import TelegramClient, sync
from telethon.tl.functions.channels import JoinChannelRequest
import sqlite3, time, logging, asyncio, requests
import config

logging.basicConfig(format='%(asctime)s %(levelname)s - %(message)s',
                    level=logging.INFO, filename='bot.log')

token = config.token

bot = telebot.TeleBot(str(token))

owner = config.owner


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn = types.KeyboardButton('Зарегистрироватьcя')
    btn2 = types.KeyboardButton('Посмотреть список пользователей')
    btn3 = types.KeyboardButton('Посмотреть список каналов')
    if owner == message.chat.id:
        markup.add(btn)
        markup.add(btn2)
        markup.add(btn3)
    else:
        markup.add(btn)
        markup.add(btn3)
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
    cursor.execute(f"SELECT id FROM user_manager WHERE id ={user_id}")
    data = cursor.fetchone()
    if data is None:
        cursor.execute(f"INSERT INTO user_manager VALUES(?, ?, ?, ?, ?, ?);",
                       (user_id, user_id, message.from_user.first_name, user_id, user_id, user_id))
        connect.commit()
        send_message = f"<b>Привет {message.from_user.first_name}!</b> Для того чтобы воспользоваться ботом нажми /instruction"
        bot.send_message(message.chat.id, send_message,
                             parse_mode='html', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f'Мы Вас помним:) Для того чтобы воспользоваться ботом нажми /instruction',
                         parse_mode='html', reply_markup=markup)


@bot.message_handler(regexp="^\d+$")
def get_id(message):
    id_ = message.text[1:]        # as string without `/`
    # id_ = int(message.text[1:])  # as integer
    bot.send_message(message.chat.id, f'{id_}')


@bot.message_handler(commands=['instruction'])
def messages(message):
        instruction = """<b>Инструкция:</b>\nДля того чтобы зарегистрироваться нажми кнопку Зарегистрироваться, предварительно нужно зарегистрировать приложение тут - Заходим в пункт "API". Ищем "Telegram API" и заходим в "Creating an application" (https://my.telegram.org/apps).\nДля того чтобы подключиться /connect (P.S. после того как нажал кнопку Зарегистрироваться и ввел данные)\nДля того чтобы добавить группу введи её ссылку, например https://t.me/durov \nДля того чтобы добавиться в группы /group_user_add"""
        bot.send_message(message.chat.id, instruction, parse_mode='html')




@bot.message_handler(commands=['group_user_add'])
def messages(message):
    connect = sqlite3.connect('group.db')
    cursor = connect.cursor()
    user_id = message.chat.id
    cursor.execute(f"SELECT id, api_id, api_hash FROM user_manager WHERE id ={user_id}")
    data = cursor.fetchall()
    print(data)
    for user in data:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            client = TelegramClient(
                f'{user[0]}', user[1], user[2], loop=loop)
            client.connect()
            cursor.execute(f"SELECT linkgroup FROM group_link WHERE chat_id={user_id}")
            group = cursor.fetchall()
            for link in group:
                links = link[0].replace("https://t.me/", "")
                print()
                try:
                    if client.is_user_authorized():
                        print(f'{user} join')
                        client(JoinChannelRequest(links))
                        time.sleep(3)
                except Exception as e:
                    print(e)
            url = "https://api.telegram.org/bot" + token
            chat_id=f'{user[0]}'
            method = url + "/sendMessage"
            text = 'Вы были добавлены в канал/-ы'
            r = requests.post(method, data={"chat_id": chat_id, "text": text})
            client.disconnect()
        except Exception as e:
            url = "https://api.telegram.org/bot" + token
            chat_id=f'{user[0]}'
            method = url + "/sendMessage"
            text = 'Была произведена попытка добавления Вас в список групп, но вы не авторизованы в приложении. Пожалуйста авторизуйтесь и нажмите команду /group_user_add!'
            r = requests.post(method, data={"chat_id": chat_id, "text": text})


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
        f"SELECT id, api_id, api_hash, phone, phone_code_hash FROM user_manager WHERE id = {user_id}")
    data = cursor.fetchone()
    if get_message_bot == 'Посмотреть список пользователей' and message.chat.id == owner:
        cursor.execute(f"SELECT * FROM user_manager")
        data = cursor.fetchall()
        message_all_user = 'Все пользователи: \n'
        for user in data:
            message_all_user += f'Менеджер: {user[2]} - Удалить: /delete_{str(user[0])}\n------\n'
        bot.send_message(message.chat.id, message_all_user, parse_mode='html')
    elif get_message_bot == 'Посмотреть список каналов':
        cursor.execute(f"SELECT * FROM group_link")
        data = cursor.fetchall()
        message_all_user = 'Список каналов: \n'
        for user in data:
            if user[1] == message.chat.id:
                message_all_user += f'Ссылка: {user[2]}\nУдалить: /delete_group_{str(user[0])}\n------\n'
        bot.send_message(message.chat.id, message_all_user, parse_mode='html')
    elif '/delete_' in get_message_bot and 'group' not in get_message_bot and message.chat.id == owner:
        user_id = get_message_bot.replace("/delete_", "")
        cursor.execute(f"DELETE FROM user_manager WHERE id = {user_id}")
        cursor.execute(f"DELETE FROM group_link WHERE chat_id = {user_id}")
        connect.commit()
        bot.send_message(
            message.chat.id, f"Пользователь с  id={user_id} удален!")
    elif '/delete_group_' in get_message_bot:
        group_id = get_message_bot.replace("/delete_group_", "")
        try:
            cursor.execute(f"DELETE FROM group_link WHERE id = ? AND chat_id=?", data)
            connect.commit()
            bot.send_message(message.chat.id, f"Группа с  id={group_id} удален!")
        except:
            bot.send_message(message.chat.id, "Вы пытаетесь удалить группу которой не существует!")
    elif ',' not in get_message_bot and "Код" not in get_message_bot and 'https://t.me/' not in get_message_bot:
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
    elif 'https://t.me/' in get_message_bot:
        connect = sqlite3.connect('group.db')
        cursor = connect.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS group_link(
            id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            linkgroup TEXT
        )""")
        connect.commit()
        get_message_bot = get_message_bot.split('\n')
        print(get_message_bot)
        for link in get_message_bot:
            data = (message.chat.id, link)
            cursor.execute(f"INSERT INTO group_link VALUES(NULL, ?, ?);", data)
            connect.commit()
        bot.send_message(message.chat.id, "Канал/-ы добавлены!")


while True:
    try:
        bot.polling(none_stop=True)  # Это нужно чтобы бот работал всё время
    except:
        time.sleep(5)  # если ошибка бот уходит в спящий режим на 5 секунд