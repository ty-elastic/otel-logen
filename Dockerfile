FROM python:3.12.6-slim-bookworm
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /python-docker

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip3 install --root-user-action=ignore -r requirements.txt

COPY _courses _courses

ARG VARIANT=none
RUN if [ -d "_courses/$VARIANT" ]; then \
        echo $VARIANT; \
        cp _courses/$VARIANT/config.yaml config.yaml; \
    fi

COPY *.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 9002
CMD [ "flask", "run", "--host=0.0.0.0", "-p", "9003" ]