import random
import ipaddress

import ua_generator
from ua_generator.options import Options
from ua_generator.data.version import VersionRange
from faker import Faker

ERROR_RETRIES = 3

CHROME_VERSIONS = (125, 135)
BROWSER_PREFERENCE = ('chrome')
BROWSER_PREFERENCE_PERCENTAGE = 30

def generate_users_per_region(regions):
    users_per_region = {}
    fake = Faker()
    for region in regions.keys():
        users_per_region[region] = []
        for i in range(regions[region]['num_customers']):
            name = fake.unique.first_name().lower() + "." + fake.unique.last_name().lower()
            user = { 'name': name }
            users_per_region[region].append(user)
    return users_per_region

def make_ua_generator_options():
    ua_generator_options = Options()
    ua_generator_options.weighted_versions = True
    ua_generator_options.version_ranges = {
        'chrome': VersionRange(CHROME_VERSIONS[0], CHROME_VERSIONS[1]),
    }
    return ua_generator_options

def generate_useragent_per_user(users_per_region, ua_generator_options):
    for region in users_per_region.keys():
        for user in users_per_region[region]:
            if random.randint(0,100) < BROWSER_PREFERENCE_PERCENTAGE:
                user['user_agent'] = ua_generator.generate(browser=BROWSER_PREFERENCE, options=ua_generator_options)
            else:
                user['user_agent'] = ua_generator.generate(options=ua_generator_options) 

def generate_ipaddress_per_user(users_per_region, regions):
    for region in users_per_region.keys():
        for user in users_per_region[region]:
            network = ipaddress.ip_network(regions[region]['ip_range'])
            ip_list = [str(ip) for ip in network]
            user['ip_address'] = random.choice(ip_list)

def get_customers(users_per_region):
    users = []
    for user in users_per_region:
        for customer in users_per_region[user]:
            users.append(customer)
    return users

def generate_request_error_per_browser(*, metadata, browser, region, error=True):
    request_error_per_customer = metadata['request_error_per_customer']
    ua_generator_options = metadata['ua_generator_options']

    for browser_version_range in ua_generator_options.version_ranges.keys():
        if browser_version_range == browser:
            last_max = ua_generator_options.version_ranges[browser].max_version.major
            ua_generator_options.version_ranges = {
                browser: VersionRange(last_max+1, last_max+1)
            }

    if region is not None:
        users = metadata['users_per_region'][region]
    else:
        users = get_customers()
    for user in users:
        if user['user_agent'].browser == browser:
            print(f'new ua for {browser}')
            user['user_agent'] = ua_generator.generate(browser=browser, options=ua_generator_options)
            if error:
                print(f"start request error for customer {user}")
                request_error_per_customer[user] = {'amount': 100, 'retries': ERROR_RETRIES}
    
    return request_error_per_customer

def generate_exception(*, metadata, item, error=True):
    found = None
    for index, exception in enumerate(metadata['exceptions']):
        if exception['messages'] == item['messages']:
            found = index
            break

    if found is None and error:
        print(f"starting exception {item}")
        metadata['exceptions'].append(item)
    elif found is not None and not error:
        print(f"stopping exception {item}")
        del metadata['exceptions'][found]

def generate_metadata(global_metadata):
    global_metadata['ua_generator_options'] = make_ua_generator_options()

    global_metadata['users_per_region'] = generate_users_per_region(global_metadata['region'])
    generate_useragent_per_user(global_metadata['users_per_region'], global_metadata['ua_generator_options'])
    generate_ipaddress_per_user(global_metadata['users_per_region'], global_metadata['region'])

    global_metadata['request_error_per_customer'] = {}
    global_metadata['stock_price'] = {}
    global_metadata['exceptions'] = []