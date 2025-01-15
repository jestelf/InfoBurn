# utils/keyboards.py
from telebot import types
import logging

logger = logging.getLogger(__name__)

def generate_markup(current, path, shared_key=None, project_name=None, page=0, items_per_page=5):
    markup = types.InlineKeyboardMarkup()
    
    if path:
        callback_data = "up" if not shared_key else f"shared_up:{shared_key}"
        markup.add(types.InlineKeyboardButton("⬆️ Вверх", callback_data=callback_data))

    # Собираем все элементы (папки и файлы) в один список
    items = []
    for folder in current["folders"]:
        if folder.endswith('.git'):
            items.append(('folder', folder, f"🔧 {folder}"))
        else:
            items.append(('folder', folder, f"📂 {folder}"))
    
    for idx, file in enumerate(current["files"], start=1):
        display_name = get_file_display_name(file, idx)
        short_id = file.get("short_id")
        if not short_id:
            logger.error(f"Файл без short_id: {file}")
            continue
        items.append(('file', short_id, display_name))

    # Пагинация
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    page = max(0, min(page, total_pages - 1))
    start = page * items_per_page
    end = start + items_per_page
    items_on_page = items[start:end]

    # Добавляем элементы текущей страницы в клавиатуру
    for item in items_on_page:
        item_type, item_id, display_name = item
        if item_type == 'folder':
            callback_data = f"folder:{item_id}" if not shared_key else f"shared_folder:{shared_key}:{item_id}"
        else:  # file
            callback_data = f"file:{item_id}" if not shared_key else f"shared_file:{shared_key}:{item_id}"
        markup.add(types.InlineKeyboardButton(display_name, callback_data=callback_data))

    # Кнопка "Вернуть Все", если есть файлы
    if current["files"]:
        if project_name:
            callback_data = "retrieve_all_project"
        else:
            callback_data = "retrieve_all" if not shared_key else f"shared_retrieve_all:{shared_key}"
        markup.add(types.InlineKeyboardButton("📤 Вернуть Все", callback_data=callback_data))

    # Добавляем кнопки навигации по страницам
    nav_buttons = []
    if page > 0:
        prev_callback = f"page:{page - 1}" if not shared_key else f"shared_page:{shared_key}:{page - 1}"
        nav_buttons.append(types.InlineKeyboardButton("⬅️", callback_data=prev_callback))
    if page < total_pages - 1:
        next_callback = f"page:{page + 1}" if not shared_key else f"shared_page:{shared_key}:{page + 1}"
        nav_buttons.append(types.InlineKeyboardButton("➡️", callback_data=next_callback))
    if nav_buttons:
        markup.row(*nav_buttons)

    if project_name:
        markup.row(
            types.InlineKeyboardButton("🌿 Создать Ветку", callback_data=f"create_branch_project:{project_name}"),
            types.InlineKeyboardButton("📜 История Коммитов", callback_data=f"log_project:{project_name}")
        )
        markup.add(types.InlineKeyboardButton("🔀 Переключиться на Ветку", callback_data=f"switch_branch_project:{project_name}"))
        markup.add(types.InlineKeyboardButton("👥 Пригласить Участника", callback_data=f"invite_member:{project_name}"))
        markup.add(types.InlineKeyboardButton("🔙 Выйти из Проекта", callback_data="exit_project"))

    return markup

def get_file_display_name(file, idx):
    file_type = file.get("type", "file")
    filename = file.get("name", f"Файл_{idx}")

    icon = "📁"

    if file_type == "text":
        icon = "📝"
    elif file_type == "document":
        icon = "📄"
    elif file_type == "photo":
        icon = "🖼️"
    elif file_type == "video":
        icon = "🎬"
    elif file_type == "audio":
        icon = "🎵"
    elif file_type == "code":
        icon = "💻"
    elif file_type == "dataset":
        icon = "📊"

    return f"{icon} {filename}"
