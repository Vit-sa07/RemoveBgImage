import telebot
from rembg import remove
from PIL import Image
import io
import sqlite3
import logging
import time
import csv

BOT_TOKEN = 'token'
ADMIN_ID = 'admin_id'

bot = telebot.TeleBot(BOT_TOKEN)

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    usage_count INTEGER DEFAULT 0
)
''')
conn.commit()


def update_user_data(user):
    cursor.execute('''
    INSERT INTO users (user_id, username, first_name, last_name, usage_count)
    VALUES (?, ?, ?, ?, 1)
    ON CONFLICT(user_id) DO UPDATE SET
        usage_count = usage_count + 1
    ''', (user.id, user.username, user.first_name, user.last_name))
    conn.commit()


def generate_csv():
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    with open('user_stats.csv', 'w', newline='') as csvfile:
        fieldnames = ['user_id', 'username', 'first_name', 'last_name', 'usage_count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for user in users:
            writer.writerow({
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'usage_count': user[4]
            })


@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = (
        "🎉 Добро пожаловать в бота для удаления фона с изображений! 🎉\n\n"
        "Отправьте мне изображение, и я удалю фон. Это займет немного времени, "
        "поэтому, пожалуйста, подождите.\n\n"
    )
    bot.reply_to(message, welcome_message)
    update_user_data(message.from_user)


@bot.message_handler(commands=['stats'])
def send_stats(message):
    if str(message.from_user.id) == ADMIN_ID:
        generate_csv()
        with open('user_stats.csv', 'rb') as csvfile:
            bot.send_document(message.chat.id, csvfile)
    else:
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.reply_to(message, "⏳ Пожалуйста, подождите, пока я удаляю фон с вашего изображения...")

        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        img = Image.open(io.BytesIO(downloaded_file))

        img_no_bg = remove(img)

        img_byte_arr = io.BytesIO()
        img_no_bg.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        bot.send_document(message.chat.id, io.BytesIO(img_byte_arr),
                          caption="✅ Фон успешно удален! Наслаждайтесь вашим изображением.",
                          visible_file_name="image_no_bg.png")

        update_user_data(message.from_user)

    except Exception as e:
        logging.error(f"Ошибка при обработке фото: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при обработке изображения. Пожалуйста, попробуйте снова.")


while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Основная ошибка в работе бота: {e}")
        time.sleep(5)
