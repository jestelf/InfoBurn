# handlers/command_handlers.py
from telebot import types
from telebot.types import Message
from utils.data_manager import (
    load_data,
    save_data,
    init_user,
    init_project,
    create_commit,
    create_branch,
    switch_branch,
    merge_branches,
    get_current_branch_structure,
    set_current_branch_structure,
    rollback_to_commit,
    get_user_id_by_username,
    is_project_member
)
from utils.navigation import navigate_to_path
from utils.keyboards import generate_markup
import uuid
import telebot

def register_command_handlers(bot: telebot.TeleBot):
    @bot.message_handler(commands=['start', 'help'])
    def handle_start_help(message: Message):
        user_id = str(message.chat.id)
        username = message.from_user.username
        data = load_data()
        init_user(data, user_id, username=username)
        save_data(data)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('/help', '/mkdir', '/cd', '/up')
        markup.row('/getmydata', '/share', '/access', '/invite')
        markup.row('/initgit', '/commit', '/branch')
        markup.row('/checkout', '/log', '/rollback', '/merge')
        bot.send_message(
            message.chat.id,
            "Добро пожаловать! Вот что я умею:\n\n"
            "/mkdir <имя_папки> - Создать новую папку\n"
            "/cd <имя_папки> - Перейти в папку\n"
            "/up - Вернуться на уровень выше\n"
            "/getmydata - Показать содержимое текущей папки\n"
            "/share - Сделать текущую папку публичной\n"
            "/access <ключ> - Получить доступ к публичной папке по ключу\n"
            "/initgit <название.git> - Инициализировать новый Git-проект\n"
            "/commit <название.git> <сообщение> - Создать коммит\n"
            "/branch <название.git> <ветка> - Создать новую ветку\n"
            "/checkout <название.git> - Переключиться на ветку\n"
            "/log <название.git> - Просмотреть историю коммитов\n"
            "/rollback <название.git> <commit_id> - Откатиться к коммиту\n"
            "/merge <название.git> <ветка_источник> <ветка_приемник> - Слить ветки\n"
            "/invite <название.git> <username> - Пригласить пользователя в проект",
            reply_markup=markup
        )

    @bot.message_handler(commands=['mkdir'])
    def handle_mkdir(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, folder_name = message.text.split(maxsplit=1)
        except ValueError:
            bot.reply_to(message, "Укажите имя папки. Пример: /mkdir НоваяПапка")
            return

        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
        if folder_name in current["folders"]:
            bot.reply_to(message, "Папка с таким именем уже существует.")
        else:
            current["folders"][folder_name] = {"folders": {}, "files": []}
            save_data(data)
            bot.reply_to(message, f"Папка '{folder_name}' создана.")

    @bot.message_handler(commands=['cd'])
    def handle_cd(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, folder_name = message.text.split(maxsplit=1)
        except ValueError:
            bot.reply_to(message, "Укажите имя папки. Пример: /cd МояПапка")
            return

        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
        if folder_name in current["folders"]:
            data["users"][user_id]["current_path"].append(folder_name)
            save_data(data)
            bot.reply_to(message, f"Перешли в папку '{folder_name}'.")
        else:
            bot.reply_to(message, "Папка не найдена.")

    @bot.message_handler(commands=['up'])
    def handle_up(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        if data["users"][user_id]["current_path"]:
            popped = data["users"][user_id]["current_path"].pop()
            save_data(data)
            bot.reply_to(message, f"Вернулись из папки '{popped}'.")
        else:
            bot.reply_to(message, "Вы уже в корневой папке.")

    @bot.message_handler(commands=['getmydata'])
    def handle_getmydata(message: Message):
        user_id = str(message.chat.id)
        username = message.from_user.username
        data = load_data()
        init_user(data, user_id, username=username)

        current_path = data["users"][user_id]["current_path"]

        # Проверяем, является ли текущая папка Git-проектом
        if current_path:
            folder_name = current_path[-1]
            if folder_name.endswith('.git'):
                project_name = folder_name
                owner_id = user_id  # По умолчанию владелец - текущий пользователь
                if "projects" in data and project_name in data["projects"][owner_id]:
                    # Проверяем, есть ли у пользователя доступ к проекту
                    if not is_project_member(data, user_id, owner_id, project_name):
                        bot.reply_to(message, f"У вас нет доступа к проекту `{project_name}`.")
                        return
                    project = data["projects"][owner_id][project_name]
                    branch_structure = get_current_branch_structure(data, owner_id, project_name)
                    # Навигация внутри проекта
                    project_path = current_path[current_path.index(project_name) + 1:]
                    current_project_folder = navigate_to_path(branch_structure, project_path)
                    markup = generate_markup(current_project_folder, current_path, project_name=project_name)
                    try:
                        bot.send_message(
                            message.chat.id,
                            f"Содержимое Git-проекта `{project_name}` (ветка `{project['current_branch']}`):",
                            reply_markup=markup
                        )
                    except telebot.apihelper.ApiTelegramException as e:
                        bot.send_message(message.chat.id, f"Ошибка при отправке клавиатуры: {str(e)}")
                    return

        # Обычная папка
        current = navigate_to_path(data["users"][user_id]["structure"], current_path)
        markup = generate_markup(current, current_path)
        try:
            bot.send_message(message.chat.id, "Ваша папочная структура:", reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            bot.send_message(message.chat.id, f"Ошибка при отправке клавиатуры: {str(e)}")

    @bot.message_handler(commands=['share'])
    def handle_share(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        current_path = data["users"][user_id]["current_path"]
        structure = data["users"][user_id]["structure"]

        # Навигация до текущей папки
        try:
            current = navigate_to_path(structure, current_path)
        except KeyError:
            bot.reply_to(message, "Текущая папка не существует.")
            return

        # Проверка, что текущая папка не пуста
        if not current["folders"] and not current["files"]:
            bot.reply_to(message, "Текущая папка пуста. Нечего делиться.")
            return

        # Генерация уникального ключа
        unique_key = uuid.uuid4().hex

        # Сохранение связи ключа с пользователем и путем
        data["shared_folders"][unique_key] = {
            "user_id": user_id,
            "path": current_path.copy()
        }

        save_data(data)

        # Отправка ключа пользователю
        bot.reply_to(
            message,
            f"Папка успешно сделана публичной.\nВаш ключ для доступа: `{unique_key}`\nИспользуйте команду /access <ключ> чтобы получить доступ.",
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['access'])
    def handle_access(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, access_key = message.text.split(maxsplit=1)
        except ValueError:
            bot.reply_to(message, "Пожалуйста, укажите ключ доступа. Пример: /access <ключ>")
            return

        shared = data.get("shared_folders", {}).get(access_key)
        if not shared:
            bot.reply_to(message, "Неверный или несуществующий ключ доступа.")
            return

        owner_id = shared["user_id"]
        path = shared["path"]

        # Проверка, существует ли пользователь и папка
        if owner_id not in data["users"]:
            bot.reply_to(message, "Владелец папки не существует.")
            return

        owner_structure = data["users"][owner_id]["structure"]
        try:
            shared_folder = navigate_to_path(owner_structure, path)
        except KeyError:
            bot.reply_to(message, "Папка не найдена.")
            return

        # Генерация клавиатуры для публичной папки
        markup = generate_markup(shared_folder, path, shared_key=access_key)

        try:
            bot.send_message(message.chat.id, "Содержимое публичной папки:", reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            bot.send_message(message.chat.id, f"Ошибка при отправке клавиатуры: {str(e)}")

    @bot.message_handler(commands=['initgit'])
    def handle_initgit(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, project_name = message.text.split(maxsplit=1)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`. Пример: MyProject.git")
                return
        except ValueError:
            bot.reply_to(message, "Укажите название проекта. Пример: /initgit MyProject.git")
            return

        if "projects" not in data:
            data["projects"] = {}
        if user_id not in data["projects"]:
            data["projects"][user_id] = {}

        if project_name in data["projects"][user_id]:
            bot.reply_to(message, f"Проект `{project_name}` уже существует.")
            return

        # Инициализация Git-проекта
        init_project(data, user_id, project_name)

        # Также создаём папку с именем проекта для хранения файлов
        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
        if project_name in current["folders"]:
            bot.reply_to(message, f"Папка `{project_name}` уже существует.")
            return
        else:
            current["folders"][project_name] = {"folders": {}, "files": []}

        save_data(data)
        bot.reply_to(message, f"Git-проект `{project_name}` успешно инициализирован.")

    @bot.message_handler(commands=['commit'])
    def handle_commit(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, project_name, commit_message = message.text.split(maxsplit=2)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`.")
                return
        except ValueError:
            bot.reply_to(message, "Использование: /commit <название.git> <сообщение>")
            return

        if "projects" not in data or project_name not in data["projects"][user_id]:
            bot.reply_to(message, f"Проект `{project_name}` не найден. Используйте /initgit для его создания.")
            return

        commit_id = create_commit(data, user_id, project_name, commit_message)
        save_data(data)
        bot.reply_to(message, f"Коммит создан. ID коммита: {commit_id}")

    @bot.message_handler(commands=['branch'])
    def handle_branch(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, project_name, branch_name = message.text.split(maxsplit=2)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`.")
                return
        except ValueError:
            bot.reply_to(message, "Использование: /branch <название.git> <ветка>")
            return

        if "projects" not in data or project_name not in data["projects"][user_id]:
            bot.reply_to(message, f"Проект `{project_name}` не найден. Используйте /initgit для его создания.")
            return

        success = create_branch(data, user_id, project_name, branch_name)
        if success:
            save_data(data)
            bot.reply_to(message, f"Ветка `{branch_name}` успешно создана и переключились на неё в проекте `{project_name}`.")
        else:
            bot.reply_to(message, f"Ветка `{branch_name}` уже существует в проекте `{project_name}`.")

    @bot.message_handler(commands=['checkout'])
    def handle_checkout(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, project_name = message.text.split(maxsplit=1)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`.")
                return
        except ValueError:
            bot.reply_to(message, "Использование: /checkout <название.git>")
            return

        if "projects" not in data or project_name not in data["projects"][user_id]:
            bot.reply_to(message, f"Проект `{project_name}` не найден. Используйте /initgit для его создания.")
            return

        project = data["projects"][user_id][project_name]
        branches = list(project["branches"].keys())
        markup = types.InlineKeyboardMarkup()
        for branch_name in branches:
            markup.add(
                types.InlineKeyboardButton(
                    branch_name, callback_data=f"switch_to_branch:{project_name}:{branch_name}"
                )
            )
        bot.send_message(message.chat.id, "Выберите ветку для переключения:", reply_markup=markup)

    @bot.message_handler(commands=['log'])
    def handle_log(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, project_name = message.text.split(maxsplit=1)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`.")
                return
        except ValueError:
            bot.reply_to(message, "Укажите название проекта. Пример: /log MyProject.git")
            return

        if "projects" not in data or project_name not in data["projects"][user_id]:
            bot.reply_to(message, f"Проект `{project_name}` не найден.")
            return

        project = data["projects"][user_id][project_name]
        branch = project["branches"][project["current_branch"]]
        commits = branch["commits"]

        if not commits:
            bot.reply_to(message, f"В проекте `{project_name}` нет коммитов.")
            return

        log_message = f"История коммитов для `{project_name}` (ветка `{project['current_branch']}`):\n\n"

        markup = telebot.types.InlineKeyboardMarkup()

        for commit in reversed(commits):  # Отображаем коммиты от новых к старым
            log_message += f"Commit ID: {commit['commit_id']}\nMessage: {commit['message']}\n\n"
            # Добавляем кнопку для отката
            markup.add(telebot.types.InlineKeyboardButton(
                f"Откатиться к коммиту {commit['commit_id']}",
                callback_data=f"rollback_commit:{project_name}:{commit['commit_id']}"
            ))

        bot.send_message(message.chat.id, log_message, reply_markup=markup)

    @bot.message_handler(commands=['rollback'])
    def handle_rollback(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, project_name, commit_id = message.text.split(maxsplit=2)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`.")
                return
            commit_id = int(commit_id)
        except ValueError:
            bot.reply_to(message, "Использование: /rollback <название.git> <commit_id>")
            return

        if "projects" not in data or project_name not in data["projects"][user_id]:
            bot.reply_to(message, f"Проект `{project_name}` не найден.")
            return

        success = rollback_to_commit(data, user_id, project_name, commit_id)
        if success:
            save_data(data)
            bot.reply_to(
                message,
                f"Откат выполнен до коммита `{commit_id}` в проекте `{project_name}`."
            )
        else:
            bot.reply_to(message, f"Коммит с ID `{commit_id}` не найден или откат не удался.")

    @bot.message_handler(commands=['merge'])
    def handle_merge(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, project_name, source_branch_name, target_branch_name = message.text.split(maxsplit=3)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`.")
                return
        except ValueError:
            bot.reply_to(message, "Использование: /merge <название.git> <ветка_источник> <ветка_приемник>")
            return

        if "projects" not in data or project_name not in data["projects"][user_id]:
            bot.reply_to(message, f"Проект `{project_name}` не найден.")
            return

        success = merge_branches(data, user_id, project_name, source_branch_name, target_branch_name)
        if success:
            save_data(data)
            bot.reply_to(
                message,
                f"Ветка `{source_branch_name}` успешно влита в ветку `{target_branch_name}` проекта `{project_name}`."
            )
        else:
            bot.reply_to(message, f"Ошибка при слиянии веток. Проверьте, что ветки существуют.")

    @bot.message_handler(commands=['invite'])
    def handle_invite(message: Message):
        user_id = str(message.chat.id)
        username = message.from_user.username
        data = load_data()
        init_user(data, user_id, username=username)

        try:
            _, project_name, invitee_username = message.text.split(maxsplit=2)
            if not project_name.endswith('.git'):
                bot.reply_to(message, "Название проекта должно заканчиваться на `.git`.")
                return
        except ValueError:
            bot.reply_to(message, "Использование: /invite <название.git> <username>")
            return

        if "projects" not in data or project_name not in data["projects"].get(user_id, {}):
            bot.reply_to(message, f"Проект `{project_name}` не найден.")
            return

        # Получаем ID приглашенного пользователя по username
        invitee_user_id = get_user_id_by_username(data, invitee_username)
        if not invitee_user_id:
            bot.reply_to(message, f"Пользователь `{invitee_username}` не найден или не взаимодействовал с ботом.")
            return

        # Добавляем пользователя в список участников проекта
        project = data["projects"][user_id][project_name]
        if "collaborators" not in project:
            project["collaborators"] = []

        if invitee_user_id not in project["collaborators"]:
            project["collaborators"].append(invitee_user_id)
            save_data(data)
            bot.reply_to(message, f"Пользователь `{invitee_username}` приглашен в проект `{project_name}`.")
            # Отправляем приглашенному пользователю уведомление
            try:
                bot.send_message(invitee_user_id, f"Вас пригласили в проект `{project_name}` пользователя @{username}.")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления: {e}")
        else:
            bot.reply_to(message, f"Пользователь `{invitee_username}` уже является участником проекта `{project_name}`.")
