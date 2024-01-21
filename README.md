# Project README

### Overview

This project is a web scraper that crawles corporate datas from rank.glassdollar.com . The application uses RabbitMQ as a message broker for Celery tasks and SpaCy for natural language processing to clustering data.

### Components

FastAPI Server (fastapi_server.py): Implements the web API, providing endpoints to initiate and get result of Celery tasks.

Celery Module (celery_module.py): Defines Celery tasks and configurations, including task queuing and processing logic.

Docker Configurations:

Dockerfile.fastapi: Sets up the FastAPI.

Dockerfile.celery: Sets up the Celery worker.

docker-compose.yml: Setup for docker compose.

Installation

Clone the repository:
`git clone https://github.com/kadirchan/glassdollar-crawl.git && cd glassdollar-crawl`

Run docker:
`docker compose up --build`

### Usage

Initiate task:
`localhost:8000/get-corporates/`

check task status:
`localhost:8000/check-task/{task_id}`

monitor celery worker:
`localhost:5555`
