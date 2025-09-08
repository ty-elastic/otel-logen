from datetime import datetime, timezone, timedelta
import random
import time

import log

DEBUG = True
ERROR_RETRIES = 3

def generate_nginx_line(*, ip, timestamp, method, url, protocol, status_code, size, ref_url, user_agent):
    line = f"{ip} - - [{timestamp}] \"{method} {url} {protocol}\" {status_code} {size} \"{ref_url}\" \"{user_agent}\"\n"
    return line

def generate_service_line(*, stock, template):
    line = template.replace('{stock.symbol}', stock['symbol'])
    line = line.replace('{stock.price}', str(stock['price']))
    return line

def generate(*, name, generator, logger, start_timestamp, end_timestamp, logs_per_second, throttled, metadata):
    timestamp = start_timestamp
    request_error_per_customer = metadata['request_error_per_customer']

    while timestamp < end_timestamp if end_timestamp is not None else True:
        region = random.choice(list(metadata['region'].keys()))
        user = random.choice(metadata['users_per_region'][region])

        symbol = random.choice(list(metadata['stock'].keys()))
        if symbol not in metadata['stock_price']:
            metadata['stock_price'][symbol] = random.randrange(metadata['stock'][symbol]['price']['min'],metadata['stock'][symbol]['price']['max'])
        metadata['stock_price'][symbol] = metadata['stock_price'][symbol] + random.randrange(-metadata['stock'][symbol]['price']['swing'],metadata['stock'][symbol]['price']['swing'])
        if metadata['stock_price'][symbol] <= metadata['stock'][symbol]['price']['min']:
            metadata['stock_price'][symbol] = metadata['stock'][symbol]['price']['min']
        stock = {
            'symbol': symbol,
            'price' : metadata['stock_price'][symbol]
        }

        lines = []
        if generator['type'] == 'nginx':
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

                line = generate_nginx_line(ip=user['ip_address'],
                                    timestamp=timestamp_str,
                                    method='POST',
                                    url=url,
                                    protocol='HTTP/1.1',
                                    status_code=200 if error_request is False else 500,
                                    size=size,
                                    ref_url='-',
                                    user_agent=user['user_agent'].text)
                lines.append(line)
                send_timestamp = send_timestamp + timedelta(seconds=1/1000)

        elif generator['type'] == 'service':

            template = None
            exceptions_indices_to_remove = []
            for index, exception in enumerate(metadata['exceptions']):
                if 'stop_minutes' in exception and 'stop_timestamp' not in exception:
                    exception['stop_timestamp'] = timestamp + timedelta(minutes=exception['stop_minutes'])
                if timestamp >= exception['stop_timestamp']:
                    print(f"stopping exception {exception}")
                    exceptions_indices_to_remove.append(index)
                    continue

                if 'filter' in exception:
                    if ('region' in exception['filter'] and exception['filter']['region'] != region):
                        continue
                if 'percent' in exception and random.randint(0, 100) < (100-exception['percent']):
                    continue
                template = random.choice(exception['messages'])
                break
            for index in exceptions_indices_to_remove:
                del metadata['exceptions'][index]

            if template is None:
                template = random.choice(generator['messages'])

            line = generate_service_line(stock=stock, template=template)
            lines.append(line)

        for line in lines:
            log.log(logger, name, timestamp, 'INFO', line)

        if throttled:
            wallclock = datetime.now(tz=timezone.utc)
            #print(f"wall={wallclock.timestamp()},time={timestamp.timestamp()}")
            delta = wallclock.timestamp() - timestamp.timestamp()
            #print(abs(delta))
            # leading
            if delta < 0:
                time.sleep(abs(delta))
        timestamp = timestamp + timedelta(seconds=1/logs_per_second)
    return timestamp
