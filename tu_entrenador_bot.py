import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# =======================
# CONFIG
# =======================
TOKEN = os.environ.get("TOKEN")  # en Render: Environment Variables -> TOKEN
if not TOKEN:
    raise RuntimeError("Falta la variable de entorno TOKEN (ponla en Render o en tu terminal).")

DATA_FILE = "data.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Estados para la conversación de perfil
GOAL, LEVEL, DAYS = range(3)

# Estados para la conversación de /hoy
MOOD, TYPE, PLACE, DURATION, DETAIL = range(3, 8)

# “Base de datos” (en memoria, pero persistida en data.json)
USER_PROFILES: Dict[str, Dict[str, Any]] = {}  # clave str para JSON estable


# =======================
# PERSISTENCIA JSON
# =======================
def load_profiles() -> Dict[str, Dict[str, Any]]:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.warning("No se pudo leer data.json: %s", e)
    return {}


def save_profiles() -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(USER_PROFILES, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("No se pudo guardar data.json: %s", e)


def uid(update: Update) -> str:
    return str(update.effective_user.id)


def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    return USER_PROFILES.get(user_id)


# Carga inicial al arrancar
USER_PROFILES = load_profiles()


# =======================
# /start - PERFIL
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_text(
        f"¡Hola {user.first_name or ''}! 👋\n\n"
        "Soy tu bot-entrenador personal.\n"
        "Primero voy a hacerte unas preguntas rápidas para adaptar los entrenos.\n\n"
        "1️⃣ ¿Cuál es tu objetivo principal?\n"
        "Responde con una opción:\n"
        "- fuerza\n- perder grasa\n- salud general"
    )
    return GOAL


async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["fuerza", "perder grasa", "salud general"]:
        await update.message.reply_text(
            "Por favor, escribe: fuerza / perder grasa / salud general."
        )
        return GOAL

    user_id = uid(update)
    USER_PROFILES.setdefault(user_id, {})
    USER_PROFILES[user_id]["goal"] = text
    save_profiles()

    reply_keyboard = [["principiante", "intermedio", "avanzado"]]
    await update.message.reply_text(
        "2️⃣ ¿Cuál es tu nivel actual?\n"
        "- principiante\n- intermedio\n- avanzado",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return LEVEL


async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["principiante", "intermedio", "avanzado"]:
        await update.message.reply_text("Elige: principiante / intermedio / avanzado.")
        return LEVEL

    user_id = uid(update)
    USER_PROFILES.setdefault(user_id, {})
    USER_PROFILES[user_id]["level"] = text
    save_profiles()

    await update.message.reply_text(
        "3️⃣ ¿Cuántos días por semana quieres entrenar? (1-7)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DAYS


async def set_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        days = int(text)
        if not (1 <= days <= 7):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Escribe un número entre 1 y 7, por ejemplo: 3")
        return DAYS

    user_id = uid(update)
    USER_PROFILES.setdefault(user_id, {})
    USER_PROFILES[user_id]["days_per_week"] = days
    save_profiles()

    profile = USER_PROFILES[user_id]
    await update.message.reply_text(
        "¡Perfecto! ✅\n\n"
        "He guardado tu perfil:\n"
        f"- Objetivo: {profile.get('goal')}\n"
        f"- Nivel: {profile.get('level')}\n"
        f"- Días/semana: {profile.get('days_per_week')}\n\n"
        "Cuando quieras un entreno, escribe /hoy 😊"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Configuración cancelada. Puedes volver a empezar con /start.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# =======================
# /hoy - ENTRENAMIENTO
# =======================
async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = uid(update)
    if user_id not in USER_PROFILES:
        await update.message.reply_text("Aún no tengo tu perfil. Escribe /start para configurarlo.")
        return ConversationHandler.END

    reply_keyboard = [["poca", "normal", "mucha"]]
    await update.message.reply_text(
        "¿Cómo te sientes hoy de energía? ⚡\n- poca\n- normal\n- mucha",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return MOOD


async def set_mood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["poca", "normal", "mucha"]:
        await update.message.reply_text("Elige: poca / normal / mucha.")
        return MOOD

    context.user_data["mood"] = text

    reply_keyboard = [["fuerza", "cardio", "movilidad"]]
    await update.message.reply_text(
        "¿Qué tipo de sesión quieres hoy?\n- fuerza\n- cardio\n- movilidad",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return TYPE


async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["fuerza", "cardio", "movilidad"]:
        await update.message.reply_text("Elige: fuerza / cardio / movilidad.")
        return TYPE

    context.user_data["session_type"] = text

    reply_keyboard = [["casa", "gym"]]
    await update.message.reply_text(
        "¿Vas a entrenar en casa o en el gym?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return PLACE


async def set_place(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if "casa" in text:
        place = "casa"
    elif "gym" in text or "gimnasio" in text:
        place = "gym"
    else:
        await update.message.reply_text("Responde 'casa' o 'gym' (o 'gimnasio').")
        return PLACE

    context.user_data["place"] = place

    await update.message.reply_text(
        "¿Cuánto tiempo tienes hoy? (10-120 min, ej: 30, 45, 60)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DURATION


async def set_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        minutes = int(text)
        if not (10 <= minutes <= 120):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Pon un número entre 10 y 120 (ej: 30).")
        return DURATION

    context.user_data["duration"] = minutes
    session_type = context.user_data.get("session_type", "fuerza")

    if session_type == "fuerza":
        await update.message.reply_text(
            "FUERZA 💪 ¿Qué quieres entrenar?\n"
            "Ej: pecho brazo abdomen / piernas glúteo / espalda hombros"
        )
    elif session_type == "cardio":
        await update.message.reply_text(
            "CARDIO 🏃‍♂️ ¿Qué cardio quieres hacer?\n"
            "Ej: correr, andar rápido, bici, elíptica, comba..."
        )
    else:
        await update.message.reply_text(
            "MOVILIDAD 🧘 ¿Qué zona quieres trabajar?\n"
            "Ej: espalda, cadera, hombros, full body..."
        )

    return DETAIL


def parse_words(text: str) -> List[str]:
    return [w.strip().lower() for w in text.replace(",", " ").split() if w.strip()]


def build_energy_tip(mood: str) -> str:
    if mood not in ["poca", "normal"]:
        return ""
    return (
        "⚠️ Para subir energía antes de entrenar:\n"
        "- Un vaso de agua.\n"
        "- 3–5 min de activación suave.\n"
        "- Snack ligero si llevas horas sin comer (fruta/yogur/frutos secos).\n\n"
    )


def build_strength_workout(profile: Dict[str, Any], mood: str, areas_text: str, place: str, duration: int) -> str:
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][datetime.now().weekday()]
    level = profile.get("level", "principiante")
    areas = parse_words(areas_text) or ["cuerpo completo"]

    area_map_home = {
        "pecho": ["Flexiones inclinadas", "Flexiones (rodillas si hace falta)"],
        "espalda": ["Remo con mochila/banda", "Superman"],
        "brazo": ["Curl bíceps con botellas", "Fondos tríceps en silla"],
        "brazos": ["Curl bíceps con botellas", "Fondos tríceps en silla"],
        "hombro": ["Elevaciones laterales", "Flexiones pica suaves"],
        "hombros": ["Elevaciones laterales", "Flexiones pica suaves"],
        "pierna": ["Sentadillas", "Zancadas"],
        "piernas": ["Sentadillas", "Zancadas"],
        "gluteo": ["Puente de glúteo", "Hip thrust en sofá"],
        "glúteo": ["Puente de glúteo", "Hip thrust en sofá"],
        "abdomen": ["Crunch", "Plancha frontal"],
        "core": ["Plancha frontal", "Plancha lateral"],
    }

    area_map_gym = {
        "pecho": ["Press banca (barra/mancuernas)", "Aperturas con mancuernas"],
        "espalda": ["Remo (barra/mancuernas)", "Jalón al pecho"],
        "brazo": ["Curl bíceps (barra/mancuernas)", "Tríceps en polea"],
        "brazos": ["Curl bíceps (barra/mancuernas)", "Tríceps en polea"],
        "hombro": ["Press militar", "Elevaciones laterales"],
        "hombros": ["Press militar", "Elevaciones laterales"],
        "pierna": ["Sentadilla", "Prensa de piernas"],
        "piernas": ["Sentadilla", "Prensa de piernas"],
        "gluteo": ["Hip thrust", "Peso muerto rumano"],
        "glúteo": ["Hip thrust", "Peso muerto rumano"],
        "abdomen": ["Crunch máquina/colchoneta", "Elevaciones de piernas"],
        "core": ["Pallof press", "Plancha"],
    }

    chosen_map = area_map_gym if place == "gym" else area_map_home

    chosen_exercises: List[str] = []
    for a in areas:
        for key, exs in chosen_map.items():
            if key in a:
                for ex in exs:
                    if ex not in chosen_exercises:
                        chosen_exercises.append(ex)

    if not chosen_exercises:
        chosen_exercises = ["Sentadillas", "Flexiones", "Remo", "Puente de glúteo", "Plancha"]

    # nº ejercicios por tiempo + energía + nº zonas
    n_areas = max(1, len(areas))
    base_ex = 4 if duration < 25 else 5 if duration < 40 else 6
    if mood == "mucha":
        base_ex += 1
    if n_areas >= 3:
        base_ex = max(base_ex, 6)
    if n_areas >= 4:
        base_ex = max(base_ex, 7)

    target_exercises = max(4, min(base_ex, 10))

    extra_pool = ["Sentadilla búlgara", "Peso muerto rumano", "Fondos en banco", "Plancha lateral", "Press hombro"]
    for ex in extra_pool:
        if len(chosen_exercises) >= target_exercises:
            break
        if ex not in chosen_exercises:
            chosen_exercises.append(ex)

    chosen_exercises = chosen_exercises[:target_exercises]

    # sets/reps
    if level == "principiante":
        sets, reps = 2, "8–12 repeticiones"
    else:
        sets, reps = 3, "10–12 repeticiones"
    if mood == "mucha" and level != "principiante" and duration >= 30:
        sets += 1

    header = (
        f"📅 {day_name}\n"
        f"🧱 FUERZA ({place}) — ~{duration} min\n"
        f"Zonas: {', '.join(areas)}\n\n"
        + build_energy_tip(mood)
    )
    body = "\n".join([f"{i+1}. {ex} — {sets} series de {reps}" for i, ex in enumerate(chosen_exercises)])
    footer = "\n\nDescansa 60–90s. Calienta 5–10 min. Si hay dolor agudo, para."
    return header + body + footer


def build_cardio_workout(profile: Dict[str, Any], mood: str, cardio_text: str, duration: int, place: str) -> str:
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][datetime.now().weekday()]
    kind = cardio_text.lower()

    warmup = max(3, int(duration * 0.15))
    cooldown = max(3, int(duration * 0.15))
    work = max(5, duration - warmup - cooldown)

    header = (
        f"📅 {day_name}\n"
        f"🏃 CARDIO ({place}) — ~{duration} min\n"
        f"Tipo: {kind}\n\n"
        + build_energy_tip(mood)
    )

    if any(k in kind for k in ["correr", "trote", "run", "cinta"]):
        main = f"- {warmup} min suave\n- {work} min alternando 1 min trote / 1 min caminar\n- {cooldown} min suave"
    elif any(k in kind for k in ["bici", "bike", "spinning"]):
        main = f"- {warmup} min suave\n- {work} min alternando 2 min moderado / 2 min suave\n- {cooldown} min suave"
    elif any(k in kind for k in ["andar", "caminar", "walk"]):
        main = f"- {warmup} min suave\n- {work} min a ritmo alegre (puedes hablar)\n- {cooldown} min suave"
    else:
        main = f"- {warmup} min suave\n- {work} min moderado\n- {cooldown} min suave"

    return header + main + "\n\nSi mareo/dolor raro: para y descansa."


def build_mobility_workout(profile: Dict[str, Any], mood: str, focus_text: str, duration: int, place: str) -> str:
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][datetime.now().weekday()]
    focus = focus_text.lower()

    header = (
        f"📅 {day_name}\n"
        f"🧘 MOVILIDAD ({place}) — ~{duration} min\n"
        f"Zona: {focus}\n\n"
        + build_energy_tip(mood)
    )

    if "espalda" in focus:
        main = "- Gato-camello 10–12\n- Rotación torácica 8–10/lado\n- Isquios 30s/lado\n- Flexor cadera 30s/lado (3 rondas)"
    elif "cadera" in focus:
        main = "- Círculos cadera 10/lado\n- Zancada estirada 30s/lado\n- Glúteo 30s/lado\n- Cuádriceps 30s/lado (3 rondas)"
    elif "hombro" in focus or "hombros" in focus:
        main = "- Círculos hombro 10+10\n- Pectoral en pared 30s/lado\n- Trapecio 30s/lado (3 rondas)"
    else:
        main = "- Círculos cuello/hombro/cadera\n- Gato-camello 10–12\n- Isquios 30s/lado\n- Pectoral 30s/lado (3 rondas)"

    return header + main + "\n\nSin dolor, respira lento."


def build_workout(profile: Dict[str, Any], mood: str, session_type: str, detail_text: str, place: str, duration: int) -> str:
    if session_type == "fuerza":
        return build_strength_workout(profile, mood, detail_text, place, duration)
    if session_type == "cardio":
        return build_cardio_workout(profile, mood, detail_text, duration, place)
    return build_mobility_workout(profile, mood, detail_text, duration, place)


async def set_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    detail_text = update.message.text.strip()
    mood = context.user_data.get("mood", "normal")
    session_type = context.user_data.get("session_type", "fuerza")
    place = context.user_data.get("place", "casa")
    duration = context.user_data.get("duration", 30)

    user_id = uid(update)
    profile = USER_PROFILES.get(user_id, {})

    workout_text = build_workout(profile, mood, session_type, detail_text, place, duration)

    await update.message.reply_text(workout_text, reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("Cuando quieras otra sesión: /hoy 💪")
    return ConversationHandler.END


async def cancel_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Entreno cancelado. Cuando quieras: /hoy",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# =======================
# COMANDOS DE PERFIL
# =======================
async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = uid(update)
    profile = USER_PROFILES.get(user_id)
    if not profile:
        await update.message.reply_text("Aún no tengo tu perfil. Usa /start.")
        return

    weight = profile.get("weight_kg")
    weight_line = f"- Peso: {weight} kg\n" if weight is not None else ""

    await update.message.reply_text(
        "📋 Tu perfil:\n"
        f"- Objetivo: {profile.get('goal')}\n"
        f"- Nivel: {profile.get('level')}\n"
        f"- Días/semana: {profile.get('days_per_week')}\n"
        f"{weight_line}\n"
        "Cambios rápidos:\n"
        "/objetivo fuerza|perder grasa|salud general\n"
        "/nivel principiante|intermedio|avanzado\n"
        "/peso 80"
    )


async def change_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = uid(update)
    if user_id not in USER_PROFILES:
        await update.message.reply_text("Primero configura tu perfil con /start.")
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Uso: /objetivo fuerza | perder grasa | salud general")
        return

    new_goal = parts[1].strip().lower()
    if new_goal not in ["fuerza", "perder grasa", "salud general"]:
        await update.message.reply_text("Objetivo no válido. Usa: fuerza / perder grasa / salud general.")
        return

    USER_PROFILES[user_id]["goal"] = new_goal
    save_profiles()
    await update.message.reply_text(f"Objetivo actualizado: {new_goal} ✅")


async def change_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = uid(update)
    if user_id not in USER_PROFILES:
        await update.message.reply_text("Primero configura tu perfil con /start.")
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Uso: /nivel principiante | intermedio | avanzado")
        return

    new_level = parts[1].strip().lower()
    if new_level not in ["principiante", "intermedio", "avanzado"]:
        await update.message.reply_text("Nivel no válido. Usa: principiante / intermedio / avanzado.")
        return

    USER_PROFILES[user_id]["level"] = new_level
    save_profiles()
    await update.message.reply_text(f"Nivel actualizado: {new_level} ✅")


async def change_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = uid(update)
    if user_id not in USER_PROFILES:
        await update.message.reply_text("Primero configura tu perfil con /start.")
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Uso: /peso 82.5")
        return

    try:
        weight = float(parts[1].strip().replace(",", "."))
        if weight <= 0 or weight > 400:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Pon un peso válido, ej: /peso 82.5")
        return

    USER_PROFILES[user_id]["weight_kg"] = weight
    save_profiles()
    await update.message.reply_text(f"Peso guardado: {weight} kg ✅")


# =======================
# MAIN
# =======================
def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    profile_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_goal)],
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_level)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    hoy_conv = ConversationHandler(
        entry_points=[CommandHandler("hoy", hoy)],
        states={
            MOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_mood)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_type)],
            PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_place)],
            DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_duration)],
            DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_detail)],
        },
        fallbacks=[CommandHandler("cancel", cancel_hoy)],
    )

    app.add_handler(profile_conv)
    app.add_handler(hoy_conv)
    app.add_handler(CommandHandler("perfil", profile_cmd))
    app.add_handler(CommandHandler("objetivo", change_goal))
    app.add_handler(CommandHandler("nivel", change_level))
    app.add_handler(CommandHandler("peso", change_weight))

    logger.info("Bot arrancando...")
    app.run_polling()


if __name__ == "__main__":
    main()
