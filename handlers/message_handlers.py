# handlers/message_handlers.py
from telebot.types import Message
from utils.data_manager import load_data, save_data, init_user, create_commit, get_current_branch_structure, set_current_branch_structure, is_project_member
from utils.navigation import navigate_to_path
import telebot
import uuid
import logging
from config import DATA_CHAT_ID

logger = logging.getLogger(__name__)

def register_message_handlers(bot: telebot.TeleBot):
    @bot.message_handler(content_types=['text', 'photo', 'document', 'video', 'audio'])
    def handle_message(message: Message):
        user_id = str(message.chat.id)
        username = message.from_user.username
        data = load_data()
        init_user(data, user_id, username=username)

        if message.content_type == 'text' and message.text.startswith('/'):
            return

        current_path = data["users"][user_id]["current_path"]

        if current_path and current_path[-1].endswith('.git'):
            project_name = current_path[-1]
            owner_id = user_id  # По умолчанию владелец - текущий пользователь

            # Проверяем, есть ли у пользователя доступ к проекту
            if not is_project_member(data, user_id, owner_id, project_name):
                bot.reply_to(message, f"У вас нет доступа к проекту `{project_name}`.")
                return

            if "projects" not in data or project_name not in data["projects"][owner_id]:
                bot.reply_to(message, f"Проект `{project_name}` не найден.")
                return

            # Получаем структуру текущей ветки
            branch_structure = get_current_branch_structure(data, owner_id, project_name)
            # Навигация внутри проекта
            project_path = current_path[current_path.index(project_name)+1:]
            current_project_folder = navigate_to_path(branch_structure, project_path)

            # Обработка файла
            if message.content_type == 'text':
                content = message.text
                file_type = 'text'
                file_name = f"message_{uuid.uuid4().hex[:8]}"
                file_entry = {
                    "type": file_type,
                    "content": content,
                    "short_id": uuid.uuid4().hex[:8],
                    "name": file_name
                }
            else:
                try:
                    copied_message = bot.copy_message(
                        chat_id=DATA_CHAT_ID,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id
                    )
                    file_type = message.content_type
                    file_name = message.document.file_name if message.document else f"file_{uuid.uuid4().hex[:8]}"
                    file_entry = {
                        "type": file_type,
                        "message_id": copied_message.message_id,
                        "short_id": uuid.uuid4().hex[:8],
                        "name": file_name
                    }
                    data["users"][user_id]["file_mappings"][file_entry["short_id"]] = copied_message.message_id
                except Exception as e:
                    logger.error(f"Ошибка при копировании сообщения: {e}")
                    bot.reply_to(message, f"Ошибка при сохранении {message.content_type}.")
                    return

            # Проверяем наличие файла с таким же именем и заменяем его
            existing_files = current_project_folder["files"]
            for idx, existing_file in enumerate(existing_files):
                if existing_file["name"] == file_name:
                    existing_files[idx] = file_entry
                    break
            else:
                # Если файл с таким именем не найден, добавляем новый
                existing_files.append(file_entry)

            # Обновляем структуру ветки
            set_current_branch_structure(data, owner_id, project_name, branch_structure)

            # Создаем коммит автоматически
            commit_message = f"Автоматический коммит: добавлен/обновлен {file_type} '{file_name}'"
            commit_id = create_commit(data, owner_id, project_name, commit_message)

            save_data(data)
            bot.reply_to(message, f"{file_type.capitalize()} '{file_name}' сохранено и закоммичено в проект `{project_name}`.")
        else:
            # Обычная обработка файлов вне Git-проекта
            current = navigate_to_path(data["users"][user_id]["structure"], current_path)
            if message.content_type == 'text':
                short_id = uuid.uuid4().hex[:8]
                current["files"].append({
                    "type": "text",
                    "content": message.text,
                    "short_id": short_id,
                    "name": f"message_{short_id}"
                })
                save_data(data)
                bot.reply_to(message, "Текстовое сообщение сохранено в текущей папке.")
            else:
                try:
                    copied_message = bot.copy_message(
                        chat_id=DATA_CHAT_ID,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id
                    )
                    short_id = uuid.uuid4().hex[:8]
                    current["files"].append({
                        "type": message.content_type,
                        "message_id": copied_message.message_id,
                        "short_id": short_id,
                        "name": message.document.file_name if message.document else f"file_{short_id}"
                    })
                    data["users"][user_id]["file_mappings"][short_id] = copied_message.message_id
                    save_data(data)
                    bot.reply_to(message, f"{message.content_type.capitalize()} сохранено в текущей папке.")
                except Exception as e:
                    logger.error(f"Ошибка при копировании сообщения: {e}")
                    bot.reply_to(message, f"Ошибка при сохранении {message.content_type}.")
