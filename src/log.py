import time
import logging
import os
import uuid

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

BACKLOG_Q_SEND_DELAY = 0.01
BACKLOG_Q_TIME_S = 60 * 60
BACKLOG_Q_BATCH_S = 60 * 2
BACKLOG_Q_TIMEOUT_MS = 10

DEBUG = False

LOG_LEVEL_LOOKUP = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

start_times = {}

def make_logger(*, service_name, max_logs_per_second):
    if not DEBUG:       
        logger_provider = LoggerProvider(
            resource=Resource.create(
                {
                    "service.name": service_name,
                    "data_stream.dataset": service_name,

                    "k8s.container.name": service_name,
                    "k8s.namespace.name": "default",
                    "k8s.deployment.name": service_name,
                    "k8s.cluster.name": "demo",
                    "k8s.pod.uid": uuid.uuid4().hex,
                    "k8s.pod.name": f"{service_name}-{uuid.uuid4().hex}",

                    "container.id": uuid.uuid4().hex
                }
            ),
        )
        if 'COLLECTOR_ADDRESS' in os.environ:
            address = os.environ['COLLECTOR_ADDRESS']
        else:
            address = "collector"
        print(f"sending logs to http://{address}:4317")
        otlp_exporter = OTLPLogExporter(endpoint=f"http://{address}:4317", insecure=True)
        processor = BatchLogRecordProcessor(
            otlp_exporter,
            schedule_delay_millis=BACKLOG_Q_TIMEOUT_MS,
            max_queue_size=BACKLOG_Q_TIME_S * max_logs_per_second,
            max_export_batch_size=BACKLOG_Q_BATCH_S * max_logs_per_second,
        )
        logger_provider.add_log_record_processor(processor)
        handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    else:
        processor = None
        handler = logging.StreamHandler()
    logger = logging.getLogger(service_name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger, processor, handler

def log_backoff(processor):
    
    if processor is not None:
        while len(processor._batch_processor._queue) == processor._batch_processor._max_queue_size:
            time.sleep(BACKLOG_Q_SEND_DELAY)
            #print('blocked')

def log(logger_tuple, name, timestamp, level, body):
    global start_times

    logger = logger_tuple[0]
    processor = logger_tuple[1]
    handler = logger_tuple[2]

    level_num = LOG_LEVEL_LOOKUP[level]

    ct = timestamp.timestamp()
    if name not in start_times:
        start_times[name] = ct
    record = logger.makeRecord(name, level_num, f'{name}.py', 0, body, None, None)
    record.created = ct
    record.msecs = ct * 1000
    record.relativeCreated = (record.created - start_times[name]) * 1000
    log_backoff(processor)
    logger.handle(record)

