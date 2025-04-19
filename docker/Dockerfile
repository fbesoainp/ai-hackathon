FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y curl

RUN pip install poetry \
    && pip install poetry-plugin-export

COPY ./pyproject.toml ./poetry.lock ./

RUN poetry export -f requirements.txt --output requirements.txt \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT [ "/app/entrypoint.sh" ]