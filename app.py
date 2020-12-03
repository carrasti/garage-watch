import os


from flask import Flask, request, json, Response
from jwcrypto.common import JWException
from jwcrypto.jwk import JWKSet
from jwcrypto.jwt import JWT

app = Flask(__name__)


_JWKSET_CONFIG = os.environ['JWKSET']
_FILE_UPLOAD_PATH = os.environ['FILE_UPLOAD_PATH']

_JWKSET = JWKSet.import_keyset(_JWKSET_CONFIG)


class AuthenticationException(Exception):
    pass


def authenticate():
    """
    Authenticate the request, this implements authentication via
    token using Authentication header

    Authentication: Bearer abcdefghijk

    Valid tokens are defined in a list the config.json file
    """
    auth_header = request.headers.get('Authentication', '')

    if not auth_header:
        raise AuthenticationException("No Authentication header")

    if not auth_header.startswith('Bearer '):
        raise AuthenticationException("Authentication header must have the format `Bearer <token>`")

    auth_token = auth_header.replace('Bearer ', '')

    auth_jwt = JWT()
    try:
        payload = auth_jwt.deserialize(auth_token, key=_JWKSET)
    except JWException as exc:
        raise AuthenticationException(str(exc)) from exc


def return_exception(exc):
    return Response(str(exc), 500, content_type='text/plain')

@app.route('/upload/', methods=['POST'])
def upload():

    # authenticate the request for starters
    try:
        authenticate()
    except AuthenticationException as exc:
        return json.jsonify({"detail": str(exc)}), 401

    # check if the post request has the file part
    if 'file' not in request.files:
        return json.jsonify({"detail": "no file provided"}), 400

    file = request.files['file']
    try:
        file.save(_FILE_UPLOAD_PATH)
    except Exception as exc:
        return json.jsonify({"detail": str(exc)}), 400
    
    return json.jsonify({'detail': 'OK'}), 201


if __name__ == '__main__':
    app.run(debug=True)
