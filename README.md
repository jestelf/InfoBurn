# InfoBurn

**InfoBurn** — телеграм-бот для управления проектами с поддержкой Git. Он упрощает работу с файлами, папками и репозиториями, а также предоставляет инструменты для совместной работы.

## Возможности

- Управление папками и файлами внутри Telegram.
- Инициализация Git-репозиториев.
- Создание веток и коммитов.
- Просмотр истории коммитов и откат к предыдущим версиям.
- Совместная работа с другими пользователями, включая управление доступом.
- Поддержка публичных папок с доступом по ключам.

## Использование

1. Установите и настройте бота, указав токен в `config.py`.
2. Запустите бота:
   ```bash
   python bot.py
   ```
3. Используйте команды в чате Telegram:
   - `/start` — начать работу с ботом.
   - `/help` — просмотреть список доступных команд.
   - `/initgit <название.git>` — инициализировать новый Git-репозиторий.
   - `/commit <название.git> <сообщение>` — создать коммит и так далее.

## Лицензия

Проект распространяется под [лицензией](https://github.com/ваш-репозиторий/LICENSE).
