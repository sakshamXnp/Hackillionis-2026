import urllib.request, json, time
from urllib.error import HTTPError

name = str(time.time())
req = urllib.request.Request(
    'http://localhost:8000/api/v1/capital-one/seed',
    method='POST',
    data=json.dumps({
        'customer': {
            'first_name': name,
            'last_name': 'B',
            'address': {'street_number': '1', 'street_name': '2', 'city': '3', 'state': '4', 'zip': '5'}
        },
        'account': {'type': 'Credit Card', 'nickname': 'C', 'rewards': 0, 'balance': 0}
    }).encode(),
    headers={'Content-Type': 'application/json'}
)
try:
    res = urllib.request.urlopen(req)
    print("SUCCESS JSON RESPONSE:")
    print(res.read().decode())
except HTTPError as e:
    print("HTTP ERROR RESPONSE:")
    print(e.read().decode())
