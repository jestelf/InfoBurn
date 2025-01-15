# handlers/callback_handlers.py
from telebot.types import CallbackQuery
from utils.data_manager import (
    load_data,
    save_data,
    init_user,
    create_branch,
    switch_branch,
    get_current_branch_structure,
    set_current_branch_structure,
    rollback_to_commit,
    get_user_id_by_username,
    is_project_member
)
from utils.navigation import navigate_to_path
from utils.keyboards import generate_markup
import telebot
import logging
from config import DATA_CHAT_ID

logger = logging.getLogger(__name__)

def register_callback_handlers(bot: telebot.TeleBot):
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery):
        user_id = str(call.message.chat.id)
        username = call.from_user.username
        data = load_data()
        init_user(data, user_id, username=username)

        if call.data == "up":
            if data["users"][user_id]["current_path"]:
                popped = data["users"][user_id]["current_path"].pop()
                bot.answer_callback_query(call.id, f"Вернулись из папки '{popped}'.")
            else:
                bot.answer_callback_query(call.id, "Вы уже в корневой папке.")
        elif call.data.startswith("page:"):
            # Обработка пагинации в обычных папках
            page = int(call.data.split(":")[1])
            current_path = data["users"][user_id]["current_path"]
            if current_path and current_path[-1].endswith('.git'):
                # Внутри Git-проекта
                project_name = current_path[-1]
                branch_structure = get_current_branch_structure(data, user_id, project_name)
                project_path = current_path[current_path.index(project_name)+1:]
                current_project_folder = navigate_to_path(branch_structure, project_path)
                markup = generate_markup(current_project_folder, current_path, project_name=project_name, page=page)
            else:
                # Обычная папка
                current = navigate_to_path(data["users"][user_id]["structure"], current_path)
                markup = generate_markup(current, current_path, page=page)
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
                bot.answer_callback_query(call.id)
            except telebot.apihelper.ApiTelegramException as e:
                logger.error(f"Ошибка при обновлении клавиатуры: {e}")
                bot.answer_callback_query(call.id, "Ошибка при обновлении клавиатуры.")
        elif call.data.startswith("shared_page:"):
            # Обработка пагинации в общих папках
            _, shared_key, page = call.data.split(":")
            page = int(page)
            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный или несуществующий ключ доступа.")
                return
            owner_id = shared["user_id"]
            path = shared["path"]
            owner_structure = data["users"][owner_id]["structure"]
            try:
                current = navigate_to_path(owner_structure, path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return
            markup = generate_markup(current, path, shared_key=shared_key, page=page)
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
                bot.answer_callback_query(call.id)
            except telebot.apihelper.ApiTelegramException as e:
                logger.error(f"Ошибка при обновлении клавиатуры: {e}")
                bot.answer_callback_query(call.id, "Ошибка при обновлении клавиатуры.")
        elif call.data.startswith("invite_member:"):
            try:
                _, project_name = call.data.split(":")
                # Проверяем, является ли пользователь владельцем проекта
                if project_name not in data["projects"].get(user_id, {}):
                    bot.answer_callback_query(call.id, f"У вас нет прав на управление проектом `{project_name}`.")
                    return
                msg = bot.send_message(call.message.chat.id, "Введите имя пользователя для приглашения:")
                bot.register_next_step_handler(msg, lambda m: handle_invite_member(m, project_name))
                bot.answer_callback_query(call.id)
            except ValueError:
                bot.answer_callback_query(call.id, "Неверный формат команды приглашения.")
                return
        elif call.data == "retrieve_all":
            # Обработка команды "Вернуть Все" в обычной папке
            current_path = data["users"][user_id]["current_path"]
            current = navigate_to_path(data["users"][user_id]["structure"], current_path)
            send_all_files(bot, call, current["files"], data, user_id)
        elif call.data.startswith("shared_retrieve_all:"):
            # Обработка команды "Вернуть Все" в общей папке
            _, shared_key = call.data.split(":")
            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный или несуществующий ключ доступа.")
                return
            owner_id = shared["user_id"]
            path = shared["path"]
            owner_structure = data["users"][owner_id]["structure"]
            try:
                current = navigate_to_path(owner_structure, path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return
            send_all_files(bot, call, current["files"], data, owner_id)
        elif call.data == "retrieve_all_project":
            # Обработка команды "Вернуть Все" в проекте
            current_path = data["users"][user_id]["current_path"]
            if current_path and current_path[-1].endswith('.git'):
                project_name = current_path[-1]
                branch_structure = get_current_branch_structure(data, user_id, project_name)
                project_path = current_path[current_path.index(project_name)+1:]
                current_project_folder = navigate_to_path(branch_structure, project_path)
                send_all_files(bot, call, current_project_folder["files"], data, user_id)
            else:
                bot.answer_callback_query(call.id, "Вы не находитесь в проекте.")
        elif call.data.startswith("folder:"):
            folder_name = call.data.split(":", 1)[1]
            current_path = data["users"][user_id]["current_path"]
            if current_path and current_path[-1].endswith('.git'):
                project_name = current_path[-1]
                branch_structure = get_current_branch_structure(data, user_id, project_name)
                project_path = current_path[current_path.index(project_name)+1:]
                current_project_folder = navigate_to_path(branch_structure, project_path)
                if folder_name in current_project_folder["folders"]:
                    data["users"][user_id]["current_path"].append(folder_name)
                    bot.answer_callback_query(call.id, f"Перешли в папку '{folder_name}'.")
                else:
                    bot.answer_callback_query(call.id, "Папка не найдена.")
            else:
                current = navigate_to_path(data["users"][user_id]["structure"], current_path)
                if folder_name in current["folders"]:
                    data["users"][user_id]["current_path"].append(folder_name)
                    bot.answer_callback_query(call.id, f"Перешли в папку '{folder_name}'.")
                else:
                    bot.answer_callback_query(call.id, "Папка не найдена.")
        elif call.data.startswith("file:"):
            short_id = call.data.split(":", 1)[1]
            file_info = None
            current_path = data["users"][user_id]["current_path"]
            if current_path and current_path[-1].endswith('.git'):
                project_name = current_path[-1]
                branch_structure = get_current_branch_structure(data, user_id, project_name)
                project_path = current_path[current_path.index(project_name)+1:]
                current_project_folder = navigate_to_path(branch_structure, project_path)
                for file in current_project_folder["files"]:
                    if file.get("short_id") == short_id:
                        file_info = file
                        break
            else:
                current = navigate_to_path(data["users"][user_id]["structure"], current_path)
                for file in current["files"]:
                    if file.get("short_id") == short_id:
                        file_info = file
                        break
            if not file_info:
                bot.answer_callback_query(call.id, "Файл не найден.")
                return
            send_file(bot, call, file_info, data, user_id)
        elif call.data.startswith("switch_branch_project:"):
            try:
                _, project_name = call.data.split(":")
                if "projects" not in data or project_name not in data["projects"][user_id]:
                    bot.answer_callback_query(call.id, f"Проект `{project_name}` не найден.")
                    return
                project = data["projects"][user_id][project_name]
                branches = list(project["branches"].keys())
                markup = telebot.types.InlineKeyboardMarkup()
                for branch_name in branches:
                    markup.add(telebot.types.InlineKeyboardButton(branch_name, callback_data=f"switch_to_branch:{project_name}:{branch_name}"))
                bot.edit_message_text("Выберите ветку для переключения:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
                bot.answer_callback_query(call.id)
            except ValueError:
                bot.answer_callback_query(call.id, "Неверный формат команды переключения ветки.")
                return
        elif call.data.startswith("switch_to_branch:"):
            try:
                _, project_name, branch_name = call.data.split(":")
                success = switch_branch(data, user_id, project_name, branch_name)
                if success:
                    save_data(data)
                    bot.answer_callback_query(call.id, f"Переключились на ветку `{branch_name}` в проекте `{project_name}`.")
                    bot.send_message(call.message.chat.id, f"Переключились на ветку `{branch_name}` в проекте `{project_name}`.")
                else:
                    bot.answer_callback_query(call.id, f"Ветка `{branch_name}` не найдена в проекте `{project_name}`.")
            except ValueError:
                bot.answer_callback_query(call.id, "Неверный формат команды переключения ветки.")
                return
        elif call.data.startswith("log_project:"):
            try:
                _, project_name = call.data.split(":")
            except ValueError:
                bot.answer_callback_query(call.id, "Неверный формат команды логов.")
                return

            if "projects" not in data or project_name not in data["projects"][user_id]:
                bot.answer_callback_query(call.id, f"Проект `{project_name}` не найден.")
                return

            project = data["projects"][user_id][project_name]
            branch = project["branches"][project["current_branch"]]
            commits = branch["commits"]

            if not commits:
                bot.send_message(call.message.chat.id, f"В проекте `{project_name}` нет коммитов в ветке `{project['current_branch']}`.")
                return

            log_message = f"История коммитов для `{project_name}` (ветка `{project['current_branch']}`):\n\n"
            for commit in commits:
                log_message += f"Commit ID: {commit['commit_id']}\nMessage: {commit['message']}\n\n"

            bot.send_message(call.message.chat.id, log_message)
            bot.answer_callback_query(call.id)
        elif call.data.startswith("rollback_commit:"):
            try:
                _, project_name, commit_id_str = call.data.split(":")
                commit_id = int(commit_id_str)
                success = rollback_to_commit(data, user_id, project_name, commit_id)
                if success:
                    save_data(data)
                    bot.answer_callback_query(call.id, f"Откатились к коммиту `{commit_id}` в проекте `{project_name}`.")
                    bot.send_message(call.message.chat.id, f"Откатились к коммиту `{commit_id}` в проекте `{project_name}`.")
                else:
                    bot.answer_callback_query(call.id, f"Коммит `{commit_id}` не найден или откат не удался.")
            except ValueError:
                bot.answer_callback_query(call.id, "Неверный формат данных для отката.")
                return
        elif call.data.startswith("create_branch_project:"):
            try:
                _, project_name = call.data.split(":")
                msg = bot.send_message(call.message.chat.id, "Введите название новой ветки:")
                bot.register_next_step_handler(msg, lambda m: handle_create_branch(m, project_name))
                bot.answer_callback_query(call.id)
            except ValueError:
                bot.answer_callback_query(call.id, "Неверный формат команды создания ветки.")
                return
        elif call.data == "exit_project":
            data["users"][user_id]["current_path"].pop()
            save_data(data)
            bot.answer_callback_query(call.id, "Вы вышли из Git-проекта.")
            bot.send_message(call.message.chat.id, "Вы вышли из Git-проекта.")
        else:
            bot.answer_callback_query(call.id, "Неизвестная команда.")

        # После обработки действий обновляем клавиатуру, если необходимо
        if call.data.startswith("folder:") or call.data == "up" or call.data == "exit_project" or call.data in ["retrieve_all", "retrieve_all_project"]:
            current_path = data["users"][user_id]["current_path"]
            if current_path and current_path[-1].endswith('.git'):
                project_name = current_path[-1]
                branch_structure = get_current_branch_structure(data, user_id, project_name)
                project_path = current_path[current_path.index(project_name)+1:]
                current_project_folder = navigate_to_path(branch_structure, project_path)
                markup = generate_markup(current_project_folder, current_path, project_name=project_name)
            else:
                current = navigate_to_path(data["users"][user_id]["structure"], current_path)
                markup = generate_markup(current, current_path)
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
                    bot.send_message(call.message.chat.id, f"Ошибка обновления клавиатуры: {str(e)}")

        save_data(data)

    def handle_invite_member(message, project_name):
        user_id = str(message.chat.id)
        username = message.from_user.username
        data = load_data()
        init_user(data, user_id, username=username)

        invitee_username = message.text.strip().lstrip("@")
        if not invitee_username:
            bot.send_message(message.chat.id, "Имя пользователя не может быть пустым.")
            return

        # Получаем ID приглашенного пользователя по username
        invitee_user_id = get_user_id_by_username(data, invitee_username)
        if not invitee_user_id:
            bot.send_message(message.chat.id, f"Пользователь `{invitee_username}` не найден или не взаимодействовал с ботом.")
            return

        # Добавляем пользователя в список участников проекта
        project = data["projects"][user_id][project_name]
        if "collaborators" not in project:
            project["collaborators"] = []

        if invitee_user_id not in project["collaborators"]:
            project["collaborators"].append(invitee_user_id)
            save_data(data)
            bot.send_message(message.chat.id, f"Пользователь `{invitee_username}` приглашен в проект `{project_name}`.")
            # Отправляем приглашенному пользователю уведомление
            try:
                bot.send_message(invitee_user_id, f"Вас пригласили в проект `{project_name}` пользователя @{username}.")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления: {e}")
        else:
            bot.send_message(message.chat.id, f"Пользователь `{invitee_username}` уже является участником проекта `{project_name}`.")

    def handle_create_branch(message, project_name):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        branch_name = message.text.strip()
        if not branch_name:
            bot.send_message(message.chat.id, "Название ветки не может быть пустым.")
            return

        if "projects" not in data or project_name not in data["projects"][user_id]:
            bot.send_message(message.chat.id, f"Проект `{project_name}` не найден.")
            return

        success = create_branch(data, user_id, project_name, branch_name)
        if success:
            save_data(data)
            bot.send_message(message.chat.id, f"Ветка `{branch_name}` успешно создана и переключились на неё в проекте `{project_name}`.")
        else:
            bot.send_message(message.chat.id, f"Ветка `{branch_name}` уже существует в проекте `{project_name}`.")

    def send_all_files(bot, call, files, data, owner_id):
        if not files:
            bot.answer_callback_query(call.id, "В этой папке нет файлов.")
            return
        for file_info in files:
            send_file(bot, call, file_info, data, owner_id)
        bot.answer_callback_query(call.id, "Все файлы отправлены.")

    def send_file(bot, call, file_info, data, owner_id):
        if file_info["type"] in ["text", "code"]:
            content = file_info.get("content")
            if content:
                bot.send_message(call.message.chat.id, f"Содержимое файла:\n\n{content}")
            else:
                bot.answer_callback_query(call.id, "Невозможно отобразить содержимое файла.")
        else:
            try:
                bot.copy_message(
                    chat_id=call.message.chat.id,
                    from_chat_id=DATA_CHAT_ID,
                    message_id=file_info["message_id"]
                )
            except Exception as e:
                logger.error(f"Ошибка при копировании файла: {e}")
                bot.send_message(call.message.chat.id, f"Ошибка при отправке файла: {str(e)}")