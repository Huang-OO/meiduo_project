import base64
import pickle

from django.test import TestCase

# Create your tests here.


if __name__ == '__main__':
    dict = {
        'name': 'zs',
        'age': 123
    }

    result = pickle.dumps(dict)
    print(result)
    b = base64.b64encode(result)

    c = base64.b64encode(pickle.dumps(dict)).decode()

    print(c)