import json
from flask import request, _request_ctx_stack, abort
from functools import wraps
from jose import jwt
from urllib.request import urlopen

from constants import StatusCode

AUTH0_DOMAIN = 'udacityfsnd.auth0.com'
ALGORITHMS = ['RS256']
API_AUDIENCE = 'capstone'


class AuthError(Exception):
    '''A standardized way to communicate auth failure modes'''

    def __init__(self, error, status_code):
        """
        Constructor for AuthError

        :param self:
        :param error:
        :param status_code:
        """
        self.error = error
        self.status_code = status_code


def raise_auth_error(message, error=StatusCode.HTTP_401_UNAUTHORIZED.value):
    """
    Raise auth error with given message.

    :param message:
    :param error:
    :return:
    """
    raise AuthError({
        'success': False, 'message': message, 'error': error
    }, error)


def get_token_auth_header():
    """
    Get token from header and raise error if not possible.

    :return:
    """
    authorization = request.headers.get('Authorization')
    if not authorization:
        raise_auth_error('Missing authorization header in request headers')

    authorization_parts = authorization.split(' ')
    if authorization_parts[0].lower() != 'bearer':
        raise_auth_error('Authorization header should start with Bearer')

    elif len(authorization_parts) == 1:
        raise_auth_error('Token missing')

    elif len(authorization_parts) > 2:
        raise_auth_error('Bearer token missing')

    token = authorization_parts[1]
    return token


def check_permissions(permission, payload):
    """
    Check permissions for payload.

    :param permission:
    :param payload:
    """
    if permission in payload.get('permissions', []):
        return True

    raise_auth_error(StatusCode.HTTP_401_UNAUTHORIZED.name)


def verify_decode_jwt(token):
    """
    Verify if JWT token can be decoded or not.

    :param token:
    :return:
    """
    unverified_header = jwt.get_unverified_header(token)
    if 'kid' not in unverified_header:
        raise_auth_error('kid missing in header')

    json_url = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(json_url.read())
    rsa_key = {}

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }

    if rsa_key:
        try:
            payload = jwt.decode(
                token, rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer='https://' + AUTH0_DOMAIN + '/'
            )
            return payload

        except jwt.ExpiredSignatureError:
            raise_auth_error('Token expired')

        except jwt.JWTClaimsError:
            raise_auth_error('Check audience and issuer')

        except Exception:
            raise_auth_error(
                'Unable to parse', StatusCode.HTTP_400_BAD_REQUEST.value
            )

    raise_auth_error(
        'Issue with the key', StatusCode.HTTP_400_BAD_REQUEST.value
    )


def requires_auth(permission=''):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)
        return wrapper
    return requires_auth_decorator
