import logging
import os
from datetime import datetime
from typing import Dict, Any, List

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# ========= CONFIGURA TU TOKEN AQUÍ =========
TOKEN = os.environ["TOKEN"]
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# Estados para la conversación de perfil
GOAL, LEVEL, DAYS = range(3)

# Estados para la conversación de /hoy
MOOD, TYPE, PLACE, DURATION, DETAIL = range(3, 8)

# “Base de datos” en memoria
USER_PROFILES: Dict[int, Dict[str, Any]] = {}


# ------------------ PERFIL /start ------------------ #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_text(
        f"¡Hola {user.first_name or ''}! 👋\n\n"
        "Soy tu bot-entrenador personal.\n"
        "Primero voy a hacerte unas preguntas rápidas para adaptar los entrenos.\n\n"
        "1️⃣ ¿Cuál es tu objetivo principal?\n"
        "Responde escribiendo una de estas opciones:\n"
        "- fuerza\n- perder grasa\n- salud general"
    )
    return GOAL


async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["fuerza", "perder grasa", "salud general"]:
        await update.message.reply_text(
            "Por favor, escribe uno de estos objetivos: fuerza / perder grasa / salud general."
        )
        return GOAL

    user_id = update.effective_user.id
    USER_PROFILES.setdefault(user_id, {})
    USER_PROFILES[user_id]["goal"] = text

    reply_keyboard = [["principiante", "intermedio", "avanzado"]]
    await update.message.reply_text(
        "2️⃣ ¿Cuál es tu nivel actual de entrenamiento?\n"
        "- principiante\n- intermedio\n- avanzado",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return LEVEL


async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["principiante", "intermedio", "avanzado"]:
        await update.message.reply_text(
            "Por favor, elige: principiante / intermedio / avanzado."
        )
        return LEVEL

    user_id = update.effective_user.id
    USER_PROFILES.setdefault(user_id, {})
    USER_PROFILES[user_id]["level"] = text

    await update.message.reply_text(
        "3️⃣ ¿Cuántos días por semana quieres entrenar? (por ejemplo: 2, 3, 4, 5)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DAYS


async def set_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        days = int(text)
        if days < 1 or days > 7:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Escribe un número de días entre 1 y 7, por ejemplo: 3"
        )
        return DAYS

    user_id = update.effective_user.id
    USER_PROFILES.setdefault(user_id, {})
    USER_PROFILES[user_id]["days_per_week"] = days

    profile = USER_PROFILES[user_id]
    await update.message.reply_text(
        "¡Perfecto! ✅\n\n"
        "He guardado tu perfil:\n"
        f"- Objetivo: {profile['goal']}\n"
        f"- Nivel: {profile['level']}\n"
        f"- Días/semana: {profile['days_per_week']}\n\n"
        "Cuando quieras un entreno, escribe /hoy y te propondré una sesión "
        "según cómo te encuentres 😊"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Configuración cancelada. Puedes volver a empezar con /start.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ------------------ ENTRENAMIENTO /hoy ------------------ #

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id not in USER_PROFILES:
        await update.message.reply_text(
            "Aún no tengo tu perfil. Escribe /start para configurarlo primero."
        )
        return ConversationHandler.END

    reply_keyboard = [["poca", "normal", "mucha"]]
    await update.message.reply_text(
        "¿Cómo te sientes hoy de energía? ⚡\n"
        "- poca\n- normal\n- mucha",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return MOOD


async def set_mood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["poca", "normal", "mucha"]:
        await update.message.reply_text(
            "Elige: poca / normal / mucha."
        )
        return MOOD

    context.user_data["mood"] = text

    reply_keyboard = [["fuerza", "cardio", "movilidad"]]
    await update.message.reply_text(
        "¿Qué tipo de sesión quieres hoy?\n"
        "- fuerza\n- cardio\n- movilidad",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return TYPE


async def set_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ["fuerza", "cardio", "movilidad"]:
        await update.message.reply_text(
            "Elige: fuerza / cardio / movilidad."
        )
        return TYPE

    context.user_data["session_type"] = text

    reply_keyboard = [["casa", "gym"]]
    await update.message.reply_text(
        "¿Vas a entrenar en casa o en el gym?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return PLACE


async def set_place(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if "casa" in text:
        place = "casa"
    elif "gym" in text or "gimnasio" in text:
        place = "gym"
    else:
        await update.message.reply_text(
            "Responde 'casa' o 'gym' (o 'gimnasio')."
        )
        return PLACE

    context.user_data["place"] = place

    await update.message.reply_text(
        "¿Cuánto tiempo tienes hoy para entrenar? (en minutos, por ejemplo: 20, 30, 45, 60)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DURATION


async def set_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        minutes = int(text)
        if minutes < 10 or minutes > 120:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Pon un número de minutos entre 10 y 120, por ejemplo 30."
        )
        return DURATION

    context.user_data["duration"] = minutes
    session_type = context.user_data.get("session_type", "fuerza")

    if session_type == "fuerza":
        await update.message.reply_text(
            "Perfecto, hoy toca FUERZA 💪\n\n"
            "¿Qué quieres entrenar exactamente?\n"
            "Ejemplos: pecho brazo abdomen / piernas glúteo / espalda hombro, etc.\n"
            "Escribe las zonas que quieras trabajar:"
        )
    elif session_type == "cardio":
        await update.message.reply_text(
            "Genial, sesión de CARDIO 🏃‍♂️\n\n"
            "¿Qué tipo de cardio quieres hacer hoy?\n"
            "Ejemplos: correr, andar rápido, bici, elíptica, comba, cinta...\n"
            "Escribe lo que te apetece:"
        )
    else:  # movilidad
        await update.message.reply_text(
            "Vamos con MOVILIDAD / RECUPERACIÓN 🧘\n\n"
            "¿Qué zona quieres trabajar más?\n"
            "Ejemplos: espalda, cadera, hombros, full body, cuello...\n"
            "Escribe la zona (o 'todo el cuerpo'):"
        )

    return DETAIL


def parse_words(text: str) -> List[str]:
    return [w.strip().lower() for w in text.replace(",", " ").split() if w.strip()]


def build_energy_tip(mood: str) -> str:
    if mood not in ["poca", "normal"]:
        return ""

    tips = (
        "⚠️ Antes de empezar, prueba esto para subir un poco la energía:\n"
        "- Bebe un vaso de agua.\n"
        "- 3–5 minutos de movimiento suave (caminar por casa, pequeños saltos, movilidad básica).\n"
        "- Si ha pasado mucho desde tu última comida, toma un snack ligero (fruta, yogur, puñado de frutos secos).\n\n"
    )
    return tips


def build_strength_workout(
    profile: Dict[str, Any],
    mood: str,
    areas_text: str,
    place: str,
    duration: int,
) -> str:
    level = profile.get("level", "principiante")
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves",
                "Viernes", "Sábado", "Domingo"][datetime.now().weekday()]

    areas = parse_words(areas_text)
    if not areas:
        areas = ["cuerpo completo"]

    # mapas de ejercicios según sitio
    area_map_home = {
        "pecho": [
            "Flexiones inclinadas en mesa o sofá",
            "Flexiones en el suelo (rodillas si hace falta)",
        ],
        "espalda": [
            "Remo con mochila o banda elástica",
            "Superman tumbado boca abajo",
        ],
        "brazo": [
            "Curl de bíceps con botellas o mochila",
            "Fondos de tríceps en silla",
        ],
        "brazos": [
            "Curl de bíceps con botellas o mochila",
            "Fondos de tríceps en silla",
        ],
        "hombro": [
            "Elevaciones laterales con botellas",
            "Flexiones pica (caderas arriba) suaves",
        ],
        "hombros": [
            "Elevaciones laterales con botellas",
            "Flexiones pica (caderas arriba) suaves",
        ],
        "pierna": [
            "Sentadillas al aire",
            "Zancadas alternas",
        ],
        "piernas": [
            "Sentadillas al aire",
            "Zancadas alternas",
        ],
        "gluteo": [
            "Puente de glúteo en el suelo",
            "Hip thrust apoyando la espalda en sofá",
        ],
        "glúteo": [
            "Puente de glúteo en el suelo",
            "Hip thrust apoyando la espalda en sofá",
        ],
        "abdomen": [
            "Crunch abdominal",
            "Plancha frontal",
        ],
        "core": [
            "Plancha frontal",
            "Plancha lateral alterna",
        ],
        "cuerpo": [
            "Sentadilla + press de hombros con botellas",
            "Remo inclinado con mochila",
        ],
    }

    area_map_gym = {
        "pecho": [
            "Press banca con barra o mancuernas",
            "Aperturas con mancuernas en banco",
        ],
        "espalda": [
            "Remo con barra o mancuernas",
            "Jalón al pecho en polea",
        ],
        "brazo": [
            "Curl de bíceps con barra o mancuernas",
            "Extensión de tríceps en polea",
        ],
        "brazos": [
            "Curl de bíceps con barra o mancuernas",
            "Extensión de tríceps en polea",
        ],
        "hombro": [
            "Press militar con barra o mancuernas",
            "Elevaciones laterales en polea o mancuernas",
        ],
        "hombros": [
            "Press militar con barra o mancuernas",
            "Elevaciones laterales en polea o mancuernas",
        ],
        "pierna": [
            "Sentadilla en multipower o libre",
            "Prensa de piernas",
        ],
        "piernas": [
            "Sentadilla en multipower o libre",
            "Prensa de piernas",
        ],
        "gluteo": [
            "Hip thrust con barra",
            "Peso muerto rumano con barra o mancuernas",
        ],
        "glúteo": [
            "Hip thrust con barra",
            "Peso muerto rumano con barra o mancuernas",
        ],
        "abdomen": [
            "Crunch en máquina o en colchoneta",
            "Elevaciones de piernas en paralelas o tumbado",
        ],
        "core": [
            "Plancha con lastre opcional",
            "Pallof press en polea",
        ],
        "cuerpo": [
            "Sentadilla frontal o trasera",
            "Peso muerto rumano",
        ],
    }

    chosen_map = area_map_gym if place == "gym" else area_map_home

    chosen_exercises: List[str] = []
    for a in areas:
        for key, exs in chosen_map.items():
            if key in a:
                for ex in exs:
                    if ex not in chosen_exercises:
                        chosen_exercises.append(ex)

    # si no hemos pillado nada, rutina full body por defecto
    if not chosen_exercises:
        chosen_exercises = [
            "Sentadillas",
            "Flexiones",
            "Remo con peso",
            "Puente de glúteo",
            "Plancha frontal",
        ]

    # nº objetivo de ejercicios según tiempo, energía y nº de zonas
    n_areas = max(1, len(areas))
    if duration < 25:
        base_ex = 4
    elif duration < 40:
        base_ex = 5
    else:
        base_ex = 6

    if mood == "mucha":
        base_ex += 1

    if n_areas >= 3:
        base_ex = max(base_ex, 6)
    if n_areas >= 4:
        base_ex = max(base_ex, 7)

    target_exercises = max(4, min(base_ex, 10))

    # ampliamos o recortamos lista para aproximarnos a target_exercises
    extra_pool = [
        "Sentadilla búlgara",
        "Peso muerto rumano",
        "Remo con agarre estrecho",
        "Fondos en banco",
        "Plancha lateral",
        "Press hombro con mancuernas",
    ]
    for ex in extra_pool:
        if len(chosen_exercises) >= target_exercises:
            break
        if ex not in chosen_exercises:
            chosen_exercises.append(ex)

    if len(chosen_exercises) > target_exercises:
        chosen_exercises = chosen_exercises[:target_exercises]

    # series y repes según nivel + energía + tiempo
    level = profile.get("level", "principiante")
    if level == "principiante":
        base_sets = 2
        reps = "8–12 repeticiones"
    else:
        base_sets = 3
        reps = "10–12 repeticiones"

    if mood == "mucha" and level != "principiante" and duration >= 30:
        sets = base_sets + 1
    else:
        sets = base_sets

    header = (
        f"📅 {day_name}\n"
        f"🧱 Sesión de FUERZA ({place})\n"
        f"Duración objetivo: ~{duration} min\n"
        f"Zonas objetivo: {', '.join(areas)}\n\n"
    )
    header += build_energy_tip(mood)

    body = ""
    for i, ex in enumerate(chosen_exercises, start=1):
        body += f"{i}. {ex} – {sets} series de {reps}\n"

    body += (
        "\nCalienta antes 5–10 min con movilidad y algo de cardio suave.\n"
        "Descansa 60–90 segundos entre series.\n"
    )

    footer = (
        "\n💡 Recuerda:\n"
        "- Si sientes dolor agudo, para.\n"
        "- Adapta las repeticiones si es demasiado fácil o difícil.\n"
        "- Usa cargas que te dejen 1–3 repeticiones “en reserva” al final de cada serie.\n"
    )

    return header + body + footer


def build_cardio_workout(
    profile: Dict[str, Any],
    mood: str,
    cardio_text: str,
    duration: int,
    place: str,
) -> str:
    kind = cardio_text.lower()
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves",
                "Viernes", "Sábado", "Domingo"][datetime.now().weekday()]

    header = (
        f"📅 {day_name}\n"
        f"🏃 Sesión de CARDIO ({place})\n"
        f"Tipo: {kind}\n"
        f"Duración objetivo: ~{duration} min\n\n"
    )
    header += build_energy_tip(mood)

    warmup = max(3, int(duration * 0.15))
    cooldown = max(3, int(duration * 0.15))
    work = max(5, duration - warmup - cooldown)

    if any(k in kind for k in ["correr", "trote", "run", "cinta"]):
        if mood == "poca":
            body = (
                f"- {warmup} min caminando muy suave.\n"
                f"- {work} min alternando:\n"
                "  • 1 min trote MUY suave\n"
                "  • 2 min caminata.\n"
                f"- {cooldown} min caminando tranquilo.\n"
            )
        elif mood == "normal":
            body = (
                f"- {warmup} min calentamiento caminando.\n"
                f"- {work} min alternando:\n"
                "  • 1 min trote cómodo\n"
                "  • 1 min caminata.\n"
                f"- {cooldown} min enfriamiento.\n"
            )
        else:  # mucha
            interval = 0.5  # min rápido
            body = (
                f"- {warmup} min calentamiento (caminata + trote suave).\n"
                f"- Parte central (~{work} min):\n"
                "  • 30 s trote rápido\n"
                "  • 60–90 s muy suave.\n"
                f"- {cooldown} min enfriamiento.\n"
            )
    elif any(k in kind for k in ["bici", "bike", "spinning"]):
        body = (
            f"- {warmup} min pedaleo suave.\n"
            f"- {work} min alternando:\n"
            "  • 1–2 min algo más intenso\n"
            "  • 1–2 min suave.\n"
            f"- {cooldown} min pedaleo muy cómodo.\n"
        )
    elif any(k in kind for k in ["andar", "caminar", "walk"]):
        body = (
            f"- {warmup} min caminata muy tranquila.\n"
            f"- {work} min caminata a ritmo alegre pero pudiendo hablar.\n"
            f"- {cooldown} min bajando el ritmo.\n"
        )
    elif any(k in kind for k in ["comba", "salto"]):
        body = (
            f"- {warmup} min calentamiento (movilidad + pequeños saltos sin comba).\n"
            f"- Parte central (~{work} min): bloques de:\n"
            "  • 30 s saltos con comba\n"
            "  • 30–60 s descanso activo (caminar).\n"
            f"- {cooldown} min estiramientos suaves de gemelos y cuádriceps.\n"
        )
    else:
        body = (
            f"- {warmup} min calentamiento suave.\n"
            f"- {work} min de cardio a intensidad moderada con la actividad/aparato que elijas.\n"
            f"- {cooldown} min enfriamiento y respiración tranquila.\n"
        )

    footer = (
        "\nMantén una intensidad en la que puedas hablar con algo de esfuerzo pero sin ahogarte.\n"
        "Si notas mareo o dolor raro, para y descansa.\n"
    )

    return header + body + footer


def build_mobility_workout(
    profile: Dict[str, Any],
    mood: str,
    focus_text: str,
    duration: int,
    place: str,
) -> str:
    focus = focus_text.lower()
    day_name = ["Lunes", "Martes", "Miércoles", "Jueves",
                "Viernes", "Sábado", "Domingo"][datetime.now().weekday()]

    header = (
        f"📅 {day_name}\n"
        f"🧘 Sesión de MOVILIDAD / RECUPERACIÓN ({place})\n"
        f"Zona principal: {focus}\n"
        f"Duración aproximada: ~{duration} min\n\n"
    )
    header += build_energy_tip(mood)

    if "espalda" in focus:
        body = (
            "- Respiración diafragmática 2–3 min.\n"
            "- 3 rondas:\n"
            "  • Gato–camello (10–12 reps)\n"
            "  • Rotaciones torácicas en cuadrupedia (8–10 por lado)\n"
            "  • Estiramiento de flexores de cadera (30 s por lado)\n"
            "  • Estiramiento de isquios tumbado o de pie (30 s por lado)\n"
        )
    elif "cadera" in focus or "pierna" in focus or "piernas" in focus:
        body = (
            "- 2–3 min de marcha suave en el sitio.\n"
            "- 3 rondas:\n"
            "  • Círculos de cadera (10 por lado)\n"
            "  • Zancada estática con estiramiento de cadera (30 s por lado)\n"
            "  • Estiramiento de glúteo sentado o tumbado (30 s por lado)\n"
            "  • Estiramiento de cuádriceps de pie (30 s por lado)\n"
        )
    elif "hombro" in focus or "hombros" in focus:
        body = (
            "- 2 min de respiración tranquila.\n"
            "- 3 rondas:\n"
            "  • Círculos de hombros (10 hacia delante y 10 hacia atrás)\n"
            "  • Aperturas de pecho en cruz tumbado (10 por lado)\n"
            "  • Estiramiento de pectoral en pared (30 s por lado)\n"
            "  • Estiramiento de trapecio lateral (30 s por lado)\n"
        )
    else:
        body = (
            "- 3–5 min de movilidad general:\n"
            "  • Círculos de cuello, hombros, cadera.\n"
            "- 3 rondas de:\n"
            "  • Gato–camello (10–12 reps)\n"
            "  • Rotaciones de columna de pie (10–12 reps)\n"
            "  • Estiramiento de cadera (30 s por lado)\n"
            "  • Estiramiento de isquios (30 s por lado)\n"
            "  • Estiramiento de pectoral en pared (30 s por lado)\n"
        )

    footer = (
        "\nMuévete sin dolor, solo hasta donde notes tensión cómoda.\n"
        "Respira profundo y despacio durante todos los estiramientos.\n"
    )

    return header + body + footer


def build_workout(
    profile: Dict[str, Any],
    mood: str,
    session_type: str,
    detail_text: str,
    place: str,
    duration: int,
) -> str:
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
    user_id = update.effective_user.id
    profile = USER_PROFILES.get(user_id, {})

    workout_text = build_workout(profile, mood, session_type, detail_text, place, duration)

    await update.message.reply_text(
        workout_text,
        reply_markup=ReplyKeyboardRemove(),
    )

    await update.message.reply_text(
        "Cuando termines, me puedes contar cómo te ha ido o pedirme otra sesión con /hoy 💪"
    )

    return ConversationHandler.END


async def cancel_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Sin problema, entreno cancelado. Cuando quieras, escribe /hoy.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ------------------ COMANDOS DE PERFIL ------------------ #

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    profile = USER_PROFILES.get(user_id)
    if not profile:
        await update.message.reply_text(
            "Aún no tengo tu perfil. Usa /start para configurarlo."
        )
        return

    weight = profile.get("weight_kg")
    weight_line = f"- Peso: {weight} kg\n" if weight is not None else ""

    await update.message.reply_text(
        "📋 Tu perfil actual:\n"
        f"- Objetivo: {profile['goal']}\n"
        f"- Nivel: {profile['level']}\n"
        f"- Días/semana: {profile['days_per_week']}\n"
        f"{weight_line}\n"
        "Puedes cambiar cosas con:\n"
        "/objetivo fuerza|perder grasa|salud general\n"
        "/nivel principiante|intermedio|avanzado\n"
        "/peso 80  (tu peso en kg)\n"
    )


async def change_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in USER_PROFILES:
        await update.message.reply_text("Primero configura tu perfil con /start.")
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Usa por ejemplo: /objetivo fuerza\n"
            "Opciones: fuerza, perder grasa, salud general."
        )
        return

    new_goal = parts[1].strip().lower()
    if new_goal not in ["fuerza", "perder grasa", "salud general"]:
        await update.message.reply_text(
            "Objetivo no válido. Usa: fuerza / perder grasa / salud general."
        )
        return

    USER_PROFILES[user_id]["goal"] = new_goal
    await update.message.reply_text(f"Objetivo actualizado a: {new_goal} ✅")


async def change_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in USER_PROFILES:
        await update.message.reply_text("Primero configura tu perfil con /start.")
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Usa por ejemplo: /nivel intermedio\n"
            "Opciones: principiante, intermedio, avanzado."
        )
        return

    new_level = parts[1].strip().lower()
    if new_level not in ["principiante", "intermedio", "avanzado"]:
        await update.message.reply_text(
            "Nivel no válido. Usa: principiante / intermedio / avanzado."
        )
        return

    USER_PROFILES[user_id]["level"] = new_level
    await update.message.reply_text(f"Nivel actualizado a: {new_level} ✅")


async def change_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in USER_PROFILES:
        await update.message.reply_text("Primero configura tu perfil con /start.")
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Usa por ejemplo: /peso 80  (tu peso en kg)."
        )
        return

    try:
        weight = float(parts[1].strip().replace(",", "."))
        if weight <= 0 or weight > 400:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Pon un peso válido en kg, por ejemplo: /peso 82.5"
        )
        return

    USER_PROFILES[user_id]["weight_kg"] = weight
    await update.message.reply_text(f"Peso guardado: {weight} kg ✅")


# ------------------ MAIN ------------------ #

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    # Conversación para configurar perfil (/start)
    profile_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_goal)],
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_level)],
            DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Conversación para pedir entreno del día (/hoy)
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
