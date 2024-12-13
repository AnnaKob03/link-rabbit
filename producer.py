# import os
# import asyncio
# from aiohttp import ClientSession
# from urllib.parse import urljoin, urlparse
# from dotenv import load_dotenv
# import aio_pika
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
#
# async def publish_to_queue(channel, link):
#     await channel.default_exchange.publish(
#         aio_pika.Message(body=link.encode()),
#         routing_key=QUEUE_NAME,
#     )
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
#         # Check if the link is internal
#         if parsed_base.netloc == parsed_url.netloc:
#             links.add((full_url, link_text))
#     return links
#
#
# async def process_url(channel, url):
#     async with ClientSession() as session:
#         html = await fetch_page(session, url)
#         if html:
#             soup = BeautifulSoup(html, "html.parser")
#             page_title = soup.title.string.strip() if soup.title else "No title"
#             print(f"Страница: {page_title} ({url})")
#             links = await extract_links(html, url)
#             for link_url, link_text in links:
#                 print(f"Ссылка: {link_text} ({link_url})")
#                 await publish_to_queue(channel, link_url)
#
#
# async def main(url):
#     connection = await aio_pika.connect_robust(
#         host=RABBITMQ_HOST,
#         port=RABBITMQ_PORT,
#         login=RABBITMQ_USER,
#         password=RABBITMQ_PASSWORD,
#     )
#     async with connection:
#         channel = await connection.channel()
#         await process_url(channel, url)
#
# if __name__ == "__main__":
#     import sys
#
#     if len(sys.argv) != 2:
#         print("Usage: python producer.py <URL>")
#         sys.exit(1)
#
#     url = sys.argv[1]
#     asyncio.run(main(url))

import os
import asyncio
from aiohttp import ClientSession
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
import aio_pika
from bs4 import BeautifulSoup
from typing import Optional, Set, Tuple

# Загрузка переменных окружения
load_dotenv()

# Конфигурация RabbitMQ из переменных окружения
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
QUEUE_NAME = os.getenv("QUEUE_NAME", "links_queue")


# Вспомогательные функции
async def publish_to_queue(channel: aio_pika.Channel, link: str) -> None:
    """
    Публикует ссылку в очередь RabbitMQ.
    """
    await channel.default_exchange.publish(
        aio_pika.Message(body=link.encode()),
        routing_key=QUEUE_NAME,
    )


async def fetch_page(session: ClientSession, url: str) -> Optional[str]:
    """
    Загружает страницу по указанному URL.
    """
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        print(f"Ошибка загрузки страницы {url}: {e}")
        return None


async def extract_links(html: str, base_url: str) -> Set[Tuple[str, str]]:
    """
    Извлекает внутренние ссылки из HTML-документа.
    """
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        link_text = a_tag.get_text(strip=True) or "No text"
        full_url = urljoin(base_url, href)
        parsed_base = urlparse(base_url)
        parsed_url = urlparse(full_url)

        # Проверяем, является ли ссылка внутренней
        if parsed_base.netloc == parsed_url.netloc:
            links.add((full_url, link_text))

    return links


async def process_url(channel: aio_pika.Channel, url: str) -> None:
    """
    Обрабатывает указанный URL: загружает страницу, извлекает ссылки и публикует их в очередь.
    """
    async with ClientSession() as session:
        html = await fetch_page(session, url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            page_title = soup.title.string.strip() if soup.title else "No title"
            print(f"Страница: {page_title} ({url})")

            links = await extract_links(html, url)
            for link_url, link_text in links:
                print(f"Ссылка: {link_text} ({link_url})")
                await publish_to_queue(channel, link_url)


# Главная функция
async def main(url: str) -> None:
    """
    Основная логика приложения: подключение к RabbitMQ и обработка URL.
    """
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        login=RABBITMQ_USER,
        password=RABBITMQ_PASSWORD,
    )

    async with connection:
        channel = await connection.channel()
        await process_url(channel, url)


# Точка входа в приложение
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python producer.py <URL>")
        sys.exit(1)

    input_url = sys.argv[1]
    asyncio.run(main(input_url))
