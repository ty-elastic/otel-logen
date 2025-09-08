from flask import Flask, request, abort
from datetime import datetime, timezone, timedelta
import logging
from threading import Thread
import yaml
import time

import log_generator
import log
import metadata_generator


g_global_metadata = {}

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

@app.get('/status/realtime')
def get_realtime():
    retval = log_generator.get_realtime()
    if retval:
        return {"realtime": True}
    else:
        abort(404, description="not realtime")

@app.post('/err/browser/<browser>')
def err_request_ua(browser):
    global g_global_metadata
    region = request.args.get('region', default=None, type=str)
    return metadata_generator.generate_request_error_per_browser(browser=browser, region=region, metadata=g_global_metadata)

@app.post('/err/exception/<messages>')
def err_exception(messages):
    region = request.args.get('region', None, str)
    percent = request.args.get('percent', 100, int)
    stop_minutes = request.args.get('stop_minutes', None, int)

    item = {
        'type': "generate_exception",
        'messages': messages,
        'filter': {
            'percent': percent
        }
    }

    if region is not None:
        item['filter']['region'] = region
    if stop_minutes is not None:
        item['stop_minutes'] = stop_minutes

    return metadata_generator.generate_exception(metadata=g_global_metadata, item=item)

def run_schedule(thread, global_metadata):
    if 'metadata' not in thread:
        thread['metadata'] = {}
    if 'messages' not in thread:
        thread['messages'] = {}
    if 'language' not in thread:
        thread['language'] = 'unknown'

    metadata = global_metadata | thread['metadata']
    schedule = thread['schedule']
    thread_name = thread['name']
    messages = thread['messages']

    max_lps = 0
    for item in schedule:
        print(f'{item}')
        if 'logs_per_second' in item:
            max_lps = max(max_lps, item['logs_per_second'])

    loggers = log.make_loggers(service_name=thread_name, max_logs_per_second=max_lps, metadata=metadata, language=thread['language'])

    last_ts = schedule_start = datetime.now(tz=timezone.utc)
    print(f'start @ {schedule_start}')
    for item in schedule:
        if 'template' not in item:
            item['template'] = None

        if item['type'] == 'nginx' or item['type'] == 'service':

            if 'backfill_start_minutes' in item:
                start = schedule_start - timedelta(minutes=item['backfill_start_minutes'])
            else:
                start = last_ts

            if 'backfill_stop_minutes' in item:
                stop = schedule_start - timedelta(minutes=item['backfill_stop_minutes'])
            elif 'stop_minutes' in item:
                stop = start + timedelta(minutes=item['stop_minutes'])
            else:
                stop = None

            print(f'type={item['type']}, start={start}, stop={stop}, interval_s={1/item['logs_per_second']}')
            last_ts = log_generator.generate(thread_name=thread_name, generator=item, loggers=loggers, start_timestamp=start,
                               end_timestamp=stop, logs_per_second=item['logs_per_second'],
                               metadata=metadata, schedule_start=schedule_start, messages=messages)

        elif item['type'] == 'nginx_ua_request_errors':
            metadata_generator.generate_request_error_per_browser(browser=item['browser'], region=item['region'], metadata=global_metadata)

        elif item['type'] == 'generate_exception':
            metadata_generator.generate_exception(item=item, metadata=global_metadata)

def load_config():
    try:
        with open('config/otel-logen.yaml', 'r') as file:
            data = yaml.safe_load(file)
            return data
    except FileNotFoundError:
        print("Error: 'otel-logen.yaml' not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")

def run_threads(config):
    global g_global_metadata
    g_global_metadata = config['metadata']
    metadata_generator.generate_metadata(g_global_metadata)

    threads = []
    for thread in config['threads']:
        t = Thread(target=run_schedule, args=[thread, config['metadata']], daemon=False)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

config = load_config()
time.sleep(1)
t = Thread(target=run_threads,  args=[config], daemon=False)
t.start()

if __name__ == "__main__":
    t.join()
