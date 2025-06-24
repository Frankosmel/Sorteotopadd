import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json

# 👉 Reemplaza por tu token real
TOKEN = '7996381032:AAHGXxjLHdPp1n77RomiRZQO1L0sAzPJIyo'
bot = telebot.TeleBot(TOKEN)

# ✅ IDs de administradores
ADMINS = [1383931339, 7907625643]

# 📁 Archivos de datos
FILES = {
    "participantes": "participantes.json",       # Invitados reales
    "invitaciones": "invitaciones.json",         # Conteo referidos
    "sorteo": "sorteo.json"                      # Participantes por comando
}

# 📦 Asegurar archivos
for file in FILES.values():
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

# 📚 Funciones de archivo
def load_json(file):
    with open(file, 'r') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

# 🛡 Verifica si es admin
def es_admin(user_id):
    return user_id in ADMINS

# 🆕 Detectar cuando un usuario agrega a otro al grupo
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

# 📈 Comando /top
@bot.message_handler(commands=['top'])
def mostrar_top(message):
    chat_id = str(message.chat.id)
    invitaciones = load_json(FILES["invitaciones"]).get(chat_id, {})
    participantes = load_json(FILES["participantes"]).get(chat_id, {})

    if not invitaciones:
        bot.reply_to(message, "📉 Aún no hay invitaciones registradas.")
        return

    top = sorted(invitaciones.items(), key=lambda x: x[1], reverse=True)
    texto = "🏆 *Top Invitadores del Grupo:*\n\n"
    for i, (uid, count) in enumerate(top[:5], start=1):
        nombre = participantes.get(uid, {}).get("nombre", "Usuario")
        texto += f"{i}. {nombre} — {count} invitado(s)\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 📋 Comando /lista
@bot.message_handler(commands=['lista'])
def mostrar_lista(message):
    chat_id = str(message.chat.id)
    participantes = load_json(FILES["participantes"]).get(chat_id, {})

    if not participantes:
        bot.reply_to(message, "📭 Aún no hay participantes agregados.")
        return

    texto = "👥 *Usuarios agregados al grupo:*\n"
    for data in participantes.values():
        texto += f"• {data['nombre']}\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 🎯 Sorteo: /addsorteo
@bot.message_handler(commands=['addsorteo'])
def addsorteo(message):
    chat_id = str(message.chat.id)
    user = message.from_user
    user_id = str(user.id)

    sorteos = load_json(FILES["sorteo"])
    sorteos.setdefault(chat_id, {})
    participantes = sorteos[chat_id]

    if user_id in participantes:
        bot.reply_to(message, "🎉 ¡Ya estás anotado en el sorteo!")
        return

    participantes[user_id] = user.first_name
    save_json(FILES["sorteo"], sorteos)

    bot.reply_to(message, f"✅ ¡{user.first_name}, quedaste registrado en el sorteo! 🎁\nMucha suerte 🍀")

# 📜 Lista del sorteo: /sorteo_lista
@bot.message_handler(commands=['sorteo_lista'])
def lista_sorteo(message):
    chat_id = str(message.chat.id)
    sorteos = load_json(FILES["sorteo"]).get(chat_id, {})

    if not sorteos:
        bot.reply_to(message, "📝 Aún no hay participantes en el sorteo.")
        return

    texto = "🎉 *Participantes del Sorteo:*\n\n"
    for nombre in sorteos.values():
        texto += f"• {nombre}\n"

    bot.reply_to(message, texto, parse_mode='Markdown')

# 🛠 Panel de administración (solo en privado)
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if not es_admin(user_id):
        bot.reply_to(message, "⛔ No tienes permisos para usar este panel.")
        return

    if not message.chat.type == "private":
        bot.reply_to(message, "⚙️ El panel solo está disponible en privado.")
        return

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🧹 Reiniciar Sorteo", callback_data="reset_sorteo"),
        InlineKeyboardButton("🚫 Terminar Sorteo", callback_data="cerrar_sorteo")
    )
    markup.row(
        InlineKeyboardButton("📋 Ver Lista Sorteo", callback_data="ver_lista")
    )

    bot.send_message(user_id, "👑 *Panel de Sorteo Admin*", parse_mode='Markdown', reply_markup=markup)

# 🎛 Funciones admin con botones
@bot.callback_query_handler(func=lambda call: es_admin(call.from_user.id))
def admin_botones(call):
    chat_id = None
    sorteos = load_json(FILES["sorteo"])

    # Busca un grupo donde haya sorteo
    if sorteos:
        chat_id = list(sorteos.keys())[0]  # Usamos el primero (si hay uno activo)

    if call.data == "reset_sorteo":
        if chat_id and chat_id in sorteos:
            sorteos[chat_id] = {}
            save_json(FILES["sorteo"], sorteos)
            bot.answer_callback_query(call.id, "🔁 Sorteo reiniciado.")
            bot.edit_message_text("✅ Sorteo reiniciado.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "No hay sorteo activo.")

    elif call.data == "cerrar_sorteo":
        if chat_id and chat_id in sorteos:
            del sorteos[chat_id]
            save_json(FILES["sorteo"], sorteos)
            bot.answer_callback_query(call.id, "🚫 Sorteo cerrado.")
            bot.edit_message_text("❌ Sorteo finalizado.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "No hay sorteo para cerrar.")

    elif call.data == "ver_lista":
        if chat_id and chat_id in sorteos:
            texto = "📋 Participantes actuales:\n"
            for nombre in sorteos[chat_id].values():
                texto += f"• {nombre}\n"
            bot.send_message(call.from_user.id, texto)
        else:
            bot.send_message(call.from_user.id, "📭 No hay participantes anotados.")

# 🎬 Start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 ¡Hola! Usa /addsorteo para participar o /admin si eres organizador.")

# ▶️ Inicia el bot
print("✅ Bot activo...")
bot.infinity_polling()
