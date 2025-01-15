# utils/data_manager.py
import json
import os
from config import DATA_FILE
import logging

logger = logging.getLogger(__name__)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "shared_folders": {}, "projects": {}, "usernames": {}}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            data = update_data_format(data)
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
        return {"users": {}, "shared_folders": {}, "projects": {}, "usernames": {}}
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {e}")
        return {"users": {}, "shared_folders": {}, "projects": {}, "usernames": {}}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {e}")

def update_data_format(data):
    # Обновление данных пользователей
    for user_id, user_data in data.get("users", {}).items():
        if "file_mappings" not in user_data:
            user_data["file_mappings"] = {}
        if "username" not in user_data:
            user_data["username"] = None
    # Обновление данных проектов
    for user_id, projects in data.get("projects", {}).items():
        for project_name, project_data in projects.items():
            if "current_branch" not in project_data:
                project_data["current_branch"] = "master"
            for branch_name, branch_data in project_data.get("branches", {}).items():
                if "structure" not in branch_data:
                    branch_data["structure"] = {"folders": {}, "files": []}
                if "commits" not in branch_data:
                    branch_data["commits"] = []
            if "collaborators" not in project_data:
                project_data["collaborators"] = []
    # Инициализация usernames
    if "usernames" not in data:
        data["usernames"] = {}
    return data

def init_user(data, user_id, username=None):
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "current_path": [],
            "structure": {
                "folders": {},
                "files": []
            },
            "file_mappings": {},
            "username": username
        }
    else:
        # Обновляем username, если он изменился
        if username and data["users"][user_id].get("username") != username:
            data["users"][user_id]["username"] = username

    # Обновляем mapping username -> user_id
    if username:
        data["usernames"][username.lower()] = user_id

def init_project(data, user_id, project_name):
    if user_id not in data["projects"]:
        data["projects"][user_id] = {}
    if project_name not in data["projects"][user_id]:
        data["projects"][user_id][project_name] = {
            "branches": {
                "master": {
                    "commits": [],
                    "structure": {
                        "folders": {},
                        "files": []
                    }
                }
            },
            "current_branch": "master",
            "collaborators": []
        }

def create_commit(data, user_id, project_name, commit_message):
    import copy
    project = data["projects"][user_id][project_name]
    branch = project["branches"][project["current_branch"]]

    # Убедимся, что ключ 'structure' существует
    if "structure" not in branch:
        branch["structure"] = {"folders": {}, "files": []}

    commit_id = len(branch["commits"]) + 1  # Простая генерация ID коммита
    # Создаем копию текущей структуры проекта для сохранения в коммит
    commit_structure = copy.deepcopy(branch["structure"])
    commit = {
        "commit_id": commit_id,
        "message": commit_message,
        "structure": commit_structure  # Сохраняем структуру в коммите
    }
    branch["commits"].append(commit)
    return commit_id

def create_branch(data, user_id, project_name, branch_name):
    import copy
    project = data["projects"][user_id][project_name]
    if branch_name in project["branches"]:
        return False
    current_branch = project["current_branch"]
    current_branch_data = project["branches"][current_branch]

    # Убедимся, что ключи существуют
    if "structure" not in current_branch_data:
        current_branch_data["structure"] = {"folders": {}, "files": []}
    if "commits" not in current_branch_data:
        current_branch_data["commits"] = []

    # Копируем структуру и коммиты текущей ветки
    project["branches"][branch_name] = {
        "commits": copy.deepcopy(current_branch_data["commits"]),
        "structure": copy.deepcopy(current_branch_data["structure"])
    }
    project["current_branch"] = branch_name
    return True

def switch_branch(data, user_id, project_name, branch_name):
    project = data["projects"][user_id][project_name]
    if branch_name not in project["branches"]:
        return False
    project["current_branch"] = branch_name
    return True

def get_current_branch_structure(data, user_id, project_name):
    project = data["projects"][user_id][project_name]
    branch = project["branches"][project["current_branch"]]

    # Убедимся, что ключ 'structure' существует
    if "structure" not in branch:
        branch["structure"] = {"folders": {}, "files": []}

    return branch["structure"]

def set_current_branch_structure(data, user_id, project_name, structure):
    project = data["projects"][user_id][project_name]
    branch = project["branches"][project["current_branch"]]

    # Убедимся, что ключ 'structure' существует
    if "structure" not in branch:
        branch["structure"] = {"folders": {}, "files": []}

    branch["structure"] = structure

def rollback_to_commit(data, user_id, project_name, commit_id):
    import copy
    project = data["projects"][user_id][project_name]
    branch = project["branches"][project["current_branch"]]

    # Убедимся, что ключи существуют
    if "commits" not in branch:
        branch["commits"] = []
    if "structure" not in branch:
        branch["structure"] = {"folders": {}, "files": []}

    commits = branch["commits"]
    if commit_id < 1 or commit_id > len(commits):
        return False
    # Откатываем коммиты
    branch["commits"] = commits[:commit_id]
    # Восстанавливаем структуру из указанного коммита
    commit = commits[commit_id - 1]
    branch["structure"] = copy.deepcopy(commit["structure"])
    return True

def merge_branches(data, user_id, project_name, source_branch_name, target_branch_name):
    import copy
    project = data["projects"][user_id][project_name]

    if source_branch_name not in project["branches"] or target_branch_name not in project["branches"]:
        return False

    source_branch = project["branches"][source_branch_name]
    target_branch = project["branches"][target_branch_name]

    # Убедимся, что ключи существуют
    if "commits" not in source_branch:
        source_branch["commits"] = []
    if "structure" not in source_branch:
        source_branch["structure"] = {"folders": {}, "files": []}
    if "commits" not in target_branch:
        target_branch["commits"] = []
    if "structure" not in target_branch:
        target_branch["structure"] = {"folders": {}, "files": []}

    # Слияние коммитов
    target_branch["commits"].extend(copy.deepcopy(source_branch["commits"][len(target_branch["commits"]):]))

    # Слияние структур
    def merge_structures(target_structure, source_structure):
        # Слияние файлов
        source_files = {file['name']: file for file in source_structure.get('files', [])}
        target_files = {file['name']: file for file in target_structure.get('files', [])}

        # Заменяем файлы в ветке-приемнике файлами из ветки-источника
        target_files.update(source_files)

        target_structure['files'] = list(target_files.values())

        # Рекурсивное слияние папок
        for folder_name, source_folder in source_structure.get('folders', {}).items():
            if folder_name not in target_structure['folders']:
                target_structure['folders'][folder_name] = copy.deepcopy(source_folder)
            else:
                merge_structures(target_structure['folders'][folder_name], source_folder)

    merge_structures(target_branch['structure'], source_branch['structure'])

    return True

def is_project_member(data, user_id, owner_id, project_name):
    if owner_id == user_id:
        return True
    project = data["projects"][owner_id][project_name]
    return user_id in project.get("collaborators", [])

def get_user_id_by_username(data, username):
    return data["usernames"].get(username.lower())

