# Async RabbitMQ Link Scraper

Проект состоит из двух консольных приложений для асинхронного извлечения ссылок с веб-страниц и обработки их через очередь сообщений RabbitMQ.

## Описание

1. **Producer**: 
   - Принимает URL через аргумент командной строки.
   - Загружает HTML-код указанного URL.
   - Находит все внутренние ссылки на странице (включая относительные и абсолютные).
   - Помещает найденные ссылки в очередь RabbitMQ.

2. **Consumer**: 
   - Читает ссылки из очереди RabbitMQ.
   - Загружает страницы по этим ссылкам.
   - Извлекает ссылки со страниц и снова помещает их в очередь.
   - Останавливается, если очередь пуста в течение заданного таймаута.

## Установка и запуск

### Предварительные требования

- Python 
- RabbitMQ
- Docker (для запуска RabbitMQ через Docker Compose, если необходимо)

### Установка зависимостей
Клонируйте репозиторий:
   ```bash
   git clone https://github.com/AnnaKob03/link-rabbit
   cd link-rabbit
   ```
Установите зависимости:

```bash
pip install -r requirements.txt
```

## Настройка .env
Создайте файл .env в корне проекта и укажите параметры подключения к RabbitMQ:
```ini
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
QUEUE_NAME=web_links
```

## Запуск RabbitMQ через Docker Compose
Если RabbitMQ не установлен локально, можно запустить его через Docker:
```bash
docker-compose up -d
```
Панель управления RabbitMQ будет доступна по адресу: http://localhost:15672 (логин/пароль: guest/guest).

## Запуск приложений
### Producer
Передайте URL как аргумент командной строки:
```bash
python producer.py https://example.com
```
### Consumer
Запустите consumer для обработки сообщений:
```bash
python consumer.py
```




