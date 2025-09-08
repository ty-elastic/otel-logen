from datetime import datetime, timezone, timedelta
import random
import time

import log
import metadata_generator

DEBUG = True
ERROR_RETRIES = 3

g_realtime = {}

def get_realtime():
    global g_realtime
    retval = True
    for thread_name in g_realtime.keys():
        if g_realtime[thread_name] is False:
            retval = False

    return retval

def form_nginx_line(*, ip, timestamp, method, url, protocol, status_code, size, ref_url, user_agent):
    line = f"{ip} - - [{timestamp}] \"{method} {url} {protocol}\" {status_code} {size} \"{ref_url}\" \"{user_agent}\"\n"
    return line

def generate_nginx_line(*, vars, timestamp, metadata):
    lines = []

    request_error_per_customer = metadata['request_error_per_customer']
    user = vars['user']

    api = random.choice(metadata['api']) 
    url=api['endpoint']
    size=random.randrange(api['payload']['min'], api['payload']['max'])

    retries = 1
    if user['name'] in request_error_per_customer:
        error_request = True if random.randint(0, 100) > (100-request_error_per_customer[user['name']]['amount']) else False
        if error_request:
            retries = request_error_per_customer[user['name']]['retries']
    else:
        error_request = False

    send_timestamp = timestamp
    for i in range(retries):
        timestamp_str = send_timestamp.strftime("%d/%b/%Y:%H:%M:%S %z")

        line = form_nginx_line(ip=user['ip_address'],
                            timestamp=timestamp_str,
                            method='POST',
                            url=url,
                            protocol='HTTP/1.1',
                            status_code=200 if error_request is False else 500,
                            size=size,
                            ref_url='-',
                            user_agent=user['user_agent'].text)
        lines.append({'body': line, 'level': "INFO"})
        send_timestamp = send_timestamp + timedelta(seconds=1/1000)
    return lines

def form_service_line(*, vars, template):
    for k,v in vars.items():
        if not isinstance(v, dict):
            template = template.replace("{" + k + "}", str(v))

    return template

def generate_service_line(*, vars, timestamp, metadata, service, messages):
    lines = []
    region = vars['region']

    message = None
    exceptions_indices_to_remove = []
    for index, exception in enumerate(metadata['exceptions']):
        if 'stop_minutes' in exception and 'stop_timestamp' not in exception:
            print("setting stop_minutes")
            exception['stop_timestamp'] = timestamp + timedelta(minutes=exception['stop_minutes'])
        if 'stop_timestamp' in exception and timestamp >= exception['stop_timestamp']:
            print(f"stopping exception {exception}")
            exceptions_indices_to_remove.append(index)
            continue

        if 'filter' in exception:
            if ('region' in exception['filter'] and exception['filter']['region'] != region):
                continue
            if 'percent' in exception['filter'] and random.randint(0, 100) < (100-exception['filter']['percent']):
                continue
        message = random.choice(messages[exception['messages']])
        break
    for index in exceptions_indices_to_remove:
        del metadata['exceptions'][index]

    if message is None:
        message = random.choice(messages[service['messages']])

    line = form_service_line(vars=vars, template=message['body'])
    lines.append({'body': line, 'level': message['level']})
    return lines

def generate(*, thread_name, name, generator, logger, start_timestamp, end_timestamp, logs_per_second, metadata, schedule_start, messages):
    global g_realtime

    timestamp = start_timestamp
    g_realtime[thread_name] = timestamp > schedule_start
    
    while timestamp < end_timestamp if end_timestamp is not None else True:
        vars = metadata_generator.generate_vars(metadata)

        lines = []
        if generator['type'] == 'nginx':
            lines = generate_nginx_line(vars=vars, timestamp=timestamp, metadata=metadata)
        elif generator['type'] == 'service':
            lines = generate_service_line(vars=vars, timestamp=timestamp, metadata=metadata, service=generator, messages=messages)

        for line in lines:
            log.log(logger, name, timestamp, line['level'], line['body'])

        if timestamp > schedule_start:
            if not g_realtime[thread_name]:
                print(f"{thread_name} realtime reached")
                g_realtime[thread_name] = True

            wallclock = datetime.now(tz=timezone.utc)
            #print(f"wall={wallclock.timestamp()},time={timestamp.timestamp()}")
            delta = wallclock.timestamp() - timestamp.timestamp()
            #print(abs(delta))
            # leading
            if delta < 0:
                time.sleep(abs(delta))
        timestamp = timestamp + timedelta(seconds=1/logs_per_second)
    return timestamp
