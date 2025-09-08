FROM python:3.12.6-slim-bookworm
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /otel-logen

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip3 install --root-user-action=ignore -r requirements.txt

COPY src/*.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 9003
CMD [ "flask", "run", "--app", "src/app", "--host=0.0.0.0", "-p", "9003"]
