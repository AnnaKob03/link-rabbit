# import os
# import asyncio
# import aiohttp
# from dotenv import load_dotenv
# import aio_pika
# from urllib.parse import urlparse, urljoin
# from bs4 import BeautifulSoup
#
# load_dotenv()
#
# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
# RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
# RABBITMQ_USER = os.getenv("RABBITMQ_USER")
# RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
# QUEUE_NAME = os.getenv("QUEUE_NAME")
#
# TIMEOUT = 10
#
#
# async def fetch_page(session, url):
#     try:
#         async with session.get(url) as response:
#             return await response.text()
#     except Exception as e:
#         print(f"Ошибка загрузки страницы {url}: {e}")
#         return None
#
#
# async def extract_links(html, base_url):
#     soup = BeautifulSoup(html, "html.parser")
#     links = set()
#     for a_tag in soup.find_all("a", href=True):
#         href = a_tag["href"]
#         link_text = a_tag.get_text(strip=True) or "No text"
#         full_url = urljoin(base_url, href)
#         parsed_base = urlparse(base_url)
#         parsed_url = urlparse(full_url)
#         if parsed_base.netloc == parsed_url.netloc:
#             links.add((full_url, link_text))
#     return links
#
#
# async def publish_to_queue(channel, link):
#     await channel.default_exchange.publish(
#         aio_pika.Message(body=link.encode()),
#         routing_key=QUEUE_NAME,
#     )
#
#
# async def process_message(channel, url):
#     async with aiohttp.ClientSession() as session:
#         html = await fetch_page(session, url)
#         if html:
#             soup = BeautifulSoup(html, "html.parser")
#             page_title = soup.title.string.strip() if soup.title else "No title"
#             print(f"Обработка страницы: {page_title} ({url})")
#             links = await extract_links(html, url)
#             for link_url, link_text in links:
#                 print(f"Найдена ссылка: {link_text} ({link_url})")
#                 await publish_to_queue(channel, link_url)
#
#
# async def consume():
#     connection = await aio_pika.connect_robust(
#         host=RABBITMQ_HOST,
#         port=RABBITMQ_PORT,
#         login=RABBITMQ_USER,
#         password=RABBITMQ_PASSWORD,
#     )
#     async with connection:
#         channel = await connection.channel()
#         queue = await channel.declare_queue(QUEUE_NAME, durable=True)
#
#         print("Ожидание сообщений...")
#
#         while True:
#             try:
#                 message = await queue.get(timeout=TIMEOUT)
#                 async with message.process():
#                     url = message.body.decode()
#                     await process_message(channel, url)
#             except aio_pika.exceptions.QueueEmpty:
#                 print(f"Нет сообщений в течение {TIMEOUT} секунд. Остановка консумера.")
#                 break
#
# if __name__ == "__main__":
#     asyncio.run(consume())

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
import aio_pika
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import logging
from typing import Set, Tuple, Optional

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Конфигурация RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
QUEUE_NAME = os.getenv("QUEUE_NAME")

# Таймаут ожидания сообщений
TIMEOUT = 10

async def fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Загружает HTML-страницу по указанному URL."""
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        logging.error(f"Ошибка загрузки страницы {url}: {e}")
        return None

async def extract_links(html: str, base_url: str) -> Set[Tuple[str, str]]:
    """Извлекает внутренние ссылки из HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        link_text = a_tag.get_text(strip=True) or "No text"
        full_url = urljoin(base_url, href)
        parsed_base = urlparse(base_url)
        parsed_url = urlparse(full_url)
        if parsed_base.netloc == parsed_url.netloc:  # Только внутренние ссылки
            links.add((full_url, link_text))
    return links

async def publish_to_queue(channel: aio_pika.Channel, link: str) -> None:
    """Публикует ссылку в очередь RabbitMQ."""
    await channel.default_exchange.publish(
        aio_pika.Message(body=link.encode()),
        routing_key=QUEUE_NAME,
    )
    logging.info(f"Ссылка опубликована: {link}")

async def process_message(channel: aio_pika.Channel, url: str) -> None:
    """Обрабатывает сообщение из очереди."""
    async with aiohttp.ClientSession() as session:
        html = await fetch_page(session, url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            page_title = soup.title.string.strip() if soup.title else "No title"
            logging.info(f"Обработка страницы: {page_title} ({url})")
            links = await extract_links(html, url)
            for link_url, link_text in links:
                logging.info(f"Найдена ссылка: {link_text} ({link_url})")
                await publish_to_queue(channel, link_url)

async def consume() -> None:
    """Основной цикл консюмера."""
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
    )
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        logging.info("Ожидание сообщений...")

        while True:
            try:
                message = await queue.get(timeout=TIMEOUT)
                async with message.process():
                    url = message.body.decode()
                    await process_message(channel, url)
            except aio_pika.exceptions.QueueEmpty:
                logging.warning(f"Нет сообщений в течение {TIMEOUT} секунд. Остановка консумера.")
                break

if __name__ == "__main__":
    asyncio.run(consume())
