import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json

TOKEN = 'AQUI_TU_TOKEN_DEL_BOT'
bot = telebot.TeleBot(TOKEN)

# Archivos de datos
PARTICIPANTES_FILE = 'data/participantes.json'
INVITACIONES_FILE = 'data/invitaciones.json'

# Asegura que existan los archivos
os.makedirs('data', exist_ok=True)
for file in [PARTICIPANTES_FILE, INVITACIONES_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

@bot.message_handler(commands=['addsorteo'])
def addsorteo(message):
    chat_id = str(message.chat.id)
    user = message.from_user
    participantes = load_json(PARTICIPANTES_FILE)
    invitaciones = load_json(INVITACIONES_FILE)

    if chat_id not in participantes:
        participantes[chat_id] = {}

    if str(user.id) in participantes[chat_id]:
        bot.reply_to(message, "🎉 ¡Ya estás participando en el sorteo!")
        return

    # Verifica si vino por referer
    texto = message.text
    referido_por = None
    if "?ref=" in texto:
        ref_id = texto.split("?ref=")[1]
        referido_por = ref_id
        if chat_id in participantes and ref_id in participantes[chat_id]:
            invitaciones.setdefault(chat_id, {})
            invitaciones[chat_id].setdefault(ref_id, 0)
            invitaciones[chat_id][ref_id] += 1

    participantes[chat_id][str(user.id)] = {
        "nombre": user.first_name,
        "referido_por": referido_por
    }

    save_json(PARTICIPANTES_FILE, participantes)
    save_json(INVITACIONES_FILE, invitaciones)

    bot.reply_to(message, f"✅ ¡{user.first_name}, estás anotado en el sorteo!")
    
    # Enviar link para invitar a otros
    link = f"https://t.me/{bot.get_me().username}?start=ref{user.id}"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔗 Invitar amigos", url=link))
    bot.send_message(chat_id, "Comparte este enlace para sumar invitados:", reply_markup=markup)

@bot.message_handler(commands=['lista'])
def ver_lista(message):
    chat_id = str(message.chat.id)
    participantes = load_json(PARTICIPANTES_FILE).get(chat_id, {})
    if not participantes:
        bot.reply_to(message, "❌ Aún no hay participantes en el sorteo.")
        return

    texto = "📋 Participantes del sorteo:\n"
    for user_id, info in participantes.items():
        texto += f"• {info['nombre']}\n"

    bot.reply_to(message, texto)

@bot.message_handler(commands=['top'])
def ver_top(message):
    chat_id = str(message.chat.id)
    invitaciones = load_json(INVITACIONES_FILE).get(chat_id, {})
    participantes = load_json(PARTICIPANTES_FILE).get(chat_id, {})

    if not invitaciones:
        bot.reply_to(message, "🤷‍♂️ Aún nadie ha invitado a otros.")
        return

    top = sorted(invitaciones.items(), key=lambda x: x[1], reverse=True)
    texto = "🏆 Top Invitadores:\n"
    for i, (uid, count) in enumerate(top[:5], start=1):
        nombre = participantes.get(uid, {}).get("nombre", "Desconocido")
        texto += f"{i}. {nombre} — {count} invitado(s)\n"

    bot.reply_to(message, texto)

# Inicio por enlace con referencia
@bot.message_handler(commands=['start'])
def start(message):
    texto = message.text
    if 'ref' in texto:
        ref_id = texto.split('ref')[1]
        message.text = f"/addsorteo?ref={ref_id}"
        addsorteo(message)
    else:
        bot.reply_to(message, "👋 ¡Hola! Usa /addsorteo para participar en el sorteo.")

bot.infinity_polling()
