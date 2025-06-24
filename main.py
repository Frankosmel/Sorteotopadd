import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json

# Token del bot
TOKEN = '7996381032:AAHGXxjLHdPp1n77RomiRZQO1L0sAzPJIyo'
bot = telebot.TeleBot(TOKEN)

# IDs de administradores autorizados
ADMINS = [1383931339, 7907625643]

# Archivos de datos
FILES = {
    "participantes": "participantes.json",
    "invitaciones": "invitaciones.json",
    "sorteo": "sorteo.json"
}

# Asegurar que existan los archivos
for file in FILES.values():
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# Función para verificar admin
def es_admin(user_id):
    return user_id in ADMINS

# Función para crear menciones con @usuario o por ID
def obtener_mencion(user):
    if user.username:
        return f"@{user.username} — ID: {user.id}"
    else:
        return f"[{user.first_name}](tg://user?id={user.id}) — ID: {user.id}"

# 🧠 Detectar quién agrega a quién al grupo
@bot.message_handler(content_types=['new_chat_members'])
def detectar_agregado(message):
    chat_id = str(message.chat.id)
    new_users = message.new_chat_members
    added_by = message.from_user

    participantes = load_json(FILES["participantes"])
    invitaciones = load_json(FILES["invitaciones"])

    participantes.setdefault(chat_id, {})
    invitaciones.setdefault(chat_id, {})

    for user in new_users:
        uid = str(user.id)
        if uid not in participantes[chat_id]:
            participantes[chat_id][uid] = {
                "nombre": user.first_name,
                "agregado_por": added_by.id
            }
            inv_id = str(added_by.id)
            invitaciones[chat_id][inv_id] = invitaciones[chat_id].get(inv_id, 0) + 1

    save_json(FILES["participantes"], participantes)
    save_json(FILES["invitaciones"], invitaciones)

# 🏆 /top — ranking de quienes han invitado más usuarios
@bot.message_handler(commands=['top'])
def mostrar_top(message):
    chat_id = str(message.chat.id)
    invitaciones = load_json(FILES["invitaciones"]).get(chat_id, {})
    participantes = load_json(FILES["participantes"]).get(chat_id, {})

    if not invitaciones:
        bot.reply_to(message, "📉 Aún nadie ha invitado a otros miembros.")
        return

    top = sorted(invitaciones.items(), key=lambda x: x[1], reverse=True)
    texto = "🏆 *Top Invitadores del Grupo:*\n\n"
    for i, (uid, count) in enumerate(top[:10], start=1):
        nombre = participantes.get(uid, {}).get("nombre", "Usuario")
        mencion = f"[{nombre}](tg://user?id={uid}) — ID: {uid}"
        texto += f"{i}. {mencion} — {count} invitado(s)\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 👥 /lista — muestra los usuarios agregados al grupo
@bot.message_handler(commands=['lista'])
def mostrar_lista(message):
    chat_id = str(message.chat.id)
    datos = load_json(FILES["participantes"]).get(chat_id, {})

    if not datos:
        bot.reply_to(message, "📭 Aún no se han registrado agregados.")
        return

    texto = "👥 *Usuarios agregados al grupo:*\n\n"
    for uid, info in datos.items():
        nombre = info["nombre"]
        texto += f"• [{nombre}](tg://user?id={uid}) — ID: {uid}\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 🎯 /addsorteo — registrarse en el sorteo
@bot.message_handler(commands=['addsorteo'])
def addsorteo(message):
    chat_id = str(message.chat.id)
    user = message.from_user
    user_id = str(user.id)

    sorteos = load_json(FILES["sorteo"])
    sorteos.setdefault(chat_id, {})

    if user_id in sorteos[chat_id]:
        bot.reply_to(message, "🎉 Ya estás participando en el sorteo.")
        return

    sorteos[chat_id][user_id] = {
        "nombre": user.first_name,
        "username": user.username
    }

    save_json(FILES["sorteo"], sorteos)

    bot.reply_to(message, f"✅ ¡{user.first_name}, has sido registrado para el sorteo!\n🎁 ¡Mucha suerte!")

# 📜 /sorteo_lista — ver quiénes están anotados
@bot.message_handler(commands=['sorteo_lista'])
def lista_sorteo(message):
    chat_id = str(message.chat.id)
    sorteos = load_json(FILES["sorteo"]).get(chat_id, {})

    if not sorteos:
        bot.reply_to(message, "📭 Aún no hay participantes registrados.")
        return

    texto = "🎁 *Participantes del Sorteo:*\n\n"
    for uid, info in sorteos.items():
        nombre = info["nombre"]
        texto += f"• [{nombre}](tg://user?id={uid}) — ID: {uid}\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 👑 /admin — solo en privado, panel para administradores
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if not es_admin(user_id):
        bot.reply_to(message, "⛔ No tienes acceso a esta función.")
        return

    if message.chat.type != "private":
        bot.reply_to(message, "ℹ️ Usa este comando en privado.")
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🧹 Reiniciar Sorteo", callback_data="reset_sorteo"),
        InlineKeyboardButton("🚫 Terminar Sorteo", callback_data="cerrar_sorteo")
    )
    markup.add(InlineKeyboardButton("📋 Ver Lista Sorteo", callback_data="ver_lista"))

    bot.send_message(user_id, "👑 *Panel de Sorteo Admin*", parse_mode='Markdown', reply_markup=markup)

# 🔘 Botones del panel admin
@bot.callback_query_handler(func=lambda call: es_admin(call.from_user.id))
def admin_opciones(call):
    sorteos = load_json(FILES["sorteo"])
    chat_id = list(sorteos.keys())[0] if sorteos else None

    if call.data == "reset_sorteo":
        if chat_id:
            sorteos[chat_id] = {}
            save_json(FILES["sorteo"], sorteos)import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json

# Token del bot
TOKEN = 'AQUI_TU_TOKEN_DEL_BOT'
bot = telebot.TeleBot(TOKEN)

# IDs de administradores autorizados
ADMINS = [1383931339, 7907625643]

# Archivos de datos
FILES = {
    "participantes": "participantes.json",
    "invitaciones": "invitaciones.json",
    "sorteo": "sorteo.json"
}

# Asegurar que existan los archivos
for file in FILES.values():
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# Función para verificar admin
def es_admin(user_id):
    return user_id in ADMINS

# Función para crear menciones con @usuario o por ID
def obtener_mencion(user):
    if user.username:
        return f"@{user.username} — ID: {user.id}"
    else:
        return f"[{user.first_name}](tg://user?id={user.id}) — ID: {user.id}"

# 🧠 Detectar quién agrega a quién al grupo
@bot.message_handler(content_types=['new_chat_members'])
def detectar_agregado(message):
    chat_id = str(message.chat.id)
    new_users = message.new_chat_members
    added_by = message.from_user

    participantes = load_json(FILES["participantes"])
    invitaciones = load_json(FILES["invitaciones"])

    participantes.setdefault(chat_id, {})
    invitaciones.setdefault(chat_id, {})

    for user in new_users:
        uid = str(user.id)
        if uid not in participantes[chat_id]:
            participantes[chat_id][uid] = {
                "nombre": user.first_name,
                "agregado_por": added_by.id
            }
            inv_id = str(added_by.id)
            invitaciones[chat_id][inv_id] = invitaciones[chat_id].get(inv_id, 0) + 1

    save_json(FILES["participantes"], participantes)
    save_json(FILES["invitaciones"], invitaciones)

# 🏆 /top — ranking de quienes han invitado más usuarios
@bot.message_handler(commands=['top'])
def mostrar_top(message):
    chat_id = str(message.chat.id)
    invitaciones = load_json(FILES["invitaciones"]).get(chat_id, {})
    participantes = load_json(FILES["participantes"]).get(chat_id, {})

    if not invitaciones:
        bot.reply_to(message, "📉 Aún nadie ha invitado a otros miembros.")
        return

    top = sorted(invitaciones.items(), key=lambda x: x[1], reverse=True)
    texto = "🏆 *Top Invitadores del Grupo:*\n\n"
    for i, (uid, count) in enumerate(top[:10], start=1):
        nombre = participantes.get(uid, {}).get("nombre", "Usuario")
        mencion = f"[{nombre}](tg://user?id={uid}) — ID: {uid}"
        texto += f"{i}. {mencion} — {count} invitado(s)\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 👥 /lista — muestra los usuarios agregados al grupo
@bot.message_handler(commands=['lista'])
def mostrar_lista(message):
    chat_id = str(message.chat.id)
    datos = load_json(FILES["participantes"]).get(chat_id, {})

    if not datos:
        bot.reply_to(message, "📭 Aún no se han registrado agregados.")
        return

    texto = "👥 *Usuarios agregados al grupo:*\n\n"
    for uid, info in datos.items():
        nombre = info["nombre"]
        texto += f"• [{nombre}](tg://user?id={uid}) — ID: {uid}\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 🎯 /addsorteo — registrarse en el sorteo
@bot.message_handler(commands=['addsorteo'])
def addsorteo(message):
    chat_id = str(message.chat.id)
    user = message.from_user
    user_id = str(user.id)

    sorteos = load_json(FILES["sorteo"])
    sorteos.setdefault(chat_id, {})

    if user_id in sorteos[chat_id]:
        bot.reply_to(message, "🎉 Ya estás participando en el sorteo.")
        return

    sorteos[chat_id][user_id] = {
        "nombre": user.first_name,
        "username": user.username
    }

    save_json(FILES["sorteo"], sorteos)

    bot.reply_to(message, f"✅ ¡{user.first_name}, has sido registrado para el sorteo!\n🎁 ¡Mucha suerte!")

# 📜 /sorteo_lista — ver quiénes están anotados
@bot.message_handler(commands=['sorteo_lista'])
def lista_sorteo(message):
    chat_id = str(message.chat.id)
    sorteos = load_json(FILES["sorteo"]).get(chat_id, {})

    if not sorteos:
        bot.reply_to(message, "📭 Aún no hay participantes registrados.")
        return

    texto = "🎁 *Participantes del Sorteo:*\n\n"
    for uid, info in sorteos.items():
        nombre = info["nombre"]
        texto += f"• [{nombre}](tg://user?id={uid}) — ID: {uid}\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 👑 /admin — solo en privado, panel para administradores
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if not es_admin(user_id):
        bot.reply_to(message, "⛔ No tienes acceso a esta función.")
        return

    if message.chat.type != "private":
        bot.reply_to(message, "ℹ️ Usa este comando en privado.")
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🧹 Reiniciar Sorteo", callback_data="reset_sorteo"),
        InlineKeyboardButton("🚫 Terminar Sorteo", callback_data="cerrar_sorteo")
    )
    markup.add(InlineKeyboardButton("📋 Ver Lista Sorteo", callback_data="ver_lista"))

    bot.send_message(user_id, "👑 *Panel de Sorteo Admin*", parse_mode='Markdown', reply_markup=markup)

# 🔘 Botones del panel admin
@bot.callback_query_handler(func=lambda call: es_admin(call.from_user.id))
def admin_opciones(call):
    sorteos = load_json(FILES["sorteo"])
    chat_id = list(sorteos.keys())[0] if sorteos else None

    if call.data == "reset_sorteo":
        if chat_id:
            sorteos[chat_id] = {}
            save_json(FILES["sorteo"], sorteos)
            bot.edit_message_text("🔁 Sorteo reiniciado exitosamente.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ No hay sorteo activo.")
    elif call.data == "cerrar_sorteo":
        if chat_id:
            del sorteos[chat_id]
            save_json(FILES["sorteo"], sorteos)
            bot.edit_message_text("❌ Sorteo cerrado.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ No hay sorteo activo.")
    elif call.data == "ver_lista":
        if chat_id and chat_id in sorteos:
            texto = "📋 Participantes actuales:\n\n"
            for uid, info in sorteos[chat_id].items():
                texto += f"• [{info['nombre']}](tg://user?id={uid}) — ID: {uid}\n"
            bot.send_message(call.from_user.id, texto, parse_mode='Markdown')
        else:
            bot.send_message(call.from_user.id, "📭 No hay participantes registrados.")

# 🟢 /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 ¡Hola! Usa /addsorteo para participar en el sorteo.\nEnvía /admin si eres organizador.")

# ▶️ Ejecutar
print("🤖 Bot en ejecución...")
bot.infinity_polling()
            bot.edit_message_text("🔁 Sorteo reiniciado exitosamente.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ No hay sorteo activo.")
    elif call.data == "cerrar_sorteo":
        if chat_id:
            del sorteos[chat_id]
            save_json(FILES["sorteo"], sorteos)
            bot.edit_message_text("❌ Sorteo cerrado.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ No hay sorteo activo.")
    elif call.data == "ver_lista":
        if chat_id and chat_id in sorteos:
            texto = "📋 Participantes actuales:\n\n"
            for uid, info in sorteos[chat_id].items():
                texto += f"• [{info['nombre']}](tg://user?id={uid}) — ID: {uid}\n"
            bot.send_message(call.from_user.id, texto, parse_mode='Markdown')
        else:
            bot.send_message(call.from_user.id, "📭 No hay participantes registrados.")

# 🟢 /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 ¡Hola! Usa /addsorteo para participar en el sorteo.\nEnvía /admin si eres organizador.")

# ▶️ Ejecutar
print("🤖 Bot en ejecución...")
bot.infinity_polling()
