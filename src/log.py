import time
import logging
import os
import uuid

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

import metadata_generator

BACKLOG_Q_SEND_DELAY = 0.01
BACKLOG_Q_TIME_S = 60 * 60
BACKLOG_Q_BATCH_S = 60 * 2
BACKLOG_Q_TIMEOUT_MS = 10

DEBUG = False

LOG_LEVEL_LOOKUP = {
    'DEBUG': 10,
    'INFO': 20,
    'WARN': 30,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50,
    'FATAL': 50
}

start_times = {}

def make_logger(*, service_name, max_logs_per_second, regional_attributes, language, mode=None):
    if not DEBUG:
        attributes = {
            "service.name": service_name,

            "k8s.container.name": service_name,
            "k8s.namespace.name": "default",
            "k8s.deployment.name": service_name,
            "k8s.pod.uid": uuid.uuid4().hex,
            "k8s.pod.name": f"{service_name}-{uuid.uuid4().hex}",

            "container.id": uuid.uuid4().hex
        }
        if mode == 'wired':
            attributes['elasticsearch.index'] = 'logs'
        else:
            attributes['data_stream.dataset'] = service_name
        if language is not None:
            attributes["telemetry.sdk.language"] = language
        host_uuid = uuid.uuid4().hex
        for key in regional_attributes.keys():
            regional_attributes[key] = regional_attributes[key].replace("{host_uuid}", host_uuid)
        attributes.update(regional_attributes)
        logger_provider = LoggerProvider(
            resource=Resource.create(attributes),
        )
        if 'COLLECTOR_ADDRESS' in os.environ:
            address = os.environ['COLLECTOR_ADDRESS']
        else:
            address = "collector"
        print(f"sending logs to http://{address}:4317 for {service_name}, {regional_attributes['cloud.availability_zone']}")
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

def make_loggers(*, service_name, max_logs_per_second, metadata, language, mode=None):
    loggers = {}

    for region in metadata_generator.get_regions(metadata):
        loggers[region] = make_logger(service_name=service_name, max_logs_per_second=max_logs_per_second, 
                                      regional_attributes=metadata_generator.get_region(metadata, region)['resource_attributes'],
                                      language=language, mode=mode)
    return loggers

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
    handler.emit(record)

