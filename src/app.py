from flask import Flask, request, abort
from datetime import datetime, timezone, timedelta
import logging
from threading import Thread
import yaml

import log_generator
import log
import metadata_generator

g_realtime = {}
g_global_metadata = {}

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

@app.get('/status/realtime')
def get_realtime():
    global g_realtime
    retval = True
    for thread_name in g_realtime.keys():
        if g_realtime[thread_name] is False:
            retval = False

    if retval:
        return {"realtime": True}
    else:
        abort(404, description="not realtime")

@app.post('/err/browser/<browser>')
def err_request_ua(browser):
    global g_global_metadata
    region = request.args.get('region', default=None, type=str)
    return metadata.generate_request_error_per_browser(browser=browser, region=region, metadata=g_global_metadata)

def run_schedule(thread_name, schedule, global_metadata, thread_metadata):
    global g_realtime
    g_realtime[thread_name] = False
    metadata = global_metadata | thread_metadata

    loggers = {}

    max_lps = 0
    for item in schedule:
        print(f'{item}')
        if 'wired' not in item:
            item['wired'] = False
        if 'logs_per_second' in item:
            max_lps = max(max_lps, item['logs_per_second'])
        if 'name' in item and item['name'] not in loggers:
            loggers[item['name']] = log.make_logger(service_name=item['name'], max_logs_per_second=max_lps)

    last_ts = schedule_start = datetime.now(tz=timezone.utc)
    print(f'start @ {schedule_start}')
    for item in schedule:
        if 'template' not in item:
            item['template'] = None

        if item['type'] == 'nginx' or item['type'] == 'service':
            if 'backfill_start_minutes' not in item:
                start = last_ts
            else:
                start = schedule_start - timedelta(minutes=item['backfill_start_minutes'])

            if 'backfill_stop_minutes' in item:
                stop = schedule_start - timedelta(minutes=item['backfill_stop_minutes'])
                throttled = False
            # real time
            else:
                if not g_realtime[thread_name]:
                    print("realtime reached")
                    g_realtime[thread_name] = True
                throttled = True
                if 'stop_minutes' in item:
                    stop = start + timedelta(minutes=item['stop_minutes'])
                else:
                    stop = None
            print(f'type={item['type']}, start={start}, stop={stop}, interval_s={1/item['logs_per_second']}')
            last_ts = log_generator.generate(name=item['name'], generator=item, logger=loggers[item['name']], start_timestamp=start, 
                               end_timestamp=stop, logs_per_second=item['logs_per_second'], throttled=throttled,
                               metadata=metadata)

        elif item['type'] == 'nginx_ua_request_errors':
            metadata_generator.generate_request_error_per_browser(browser=item['browser'], region=item['region'], metadata=global_metadata)

        elif item['type'] == 'generate_exception':
            metadata_generator.generate_exception(item=item, metadata=global_metadata)

def load_config():
    try:
        with open('config.yaml', 'r') as file:
            data = yaml.safe_load(file)
            return data
    except FileNotFoundError:
        print("Error: 'config.yaml' not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
config = load_config()

def run_threads():
    global g_global_metadata
    g_global_metadata = config['metadata']
    metadata_generator.generate_metadata(g_global_metadata)

    threads = []
    for thread in config['threads']:
        if 'metadata' not in thread:
            thread['metadata'] = {}
        t = Thread(target=run_schedule, args=[thread['name'], thread['schedule'], config['metadata'], thread['metadata']], daemon=False)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

t = Thread(target=run_threads, daemon=False)
t.start()
if __name__ == "__main__":
    t.join()
