import os

import math
from flask import Flask, request, json, Response
from jwcrypto.common import JWException
from jwcrypto.jwk import JWKSet
from jwcrypto.jwt import JWT

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

_JWKSET_PATH = os.environ["JWKSET_PATH"]
_FILE_UPLOAD_PATH = os.environ["FILE_UPLOAD_PATH"]

with open(_JWKSET_PATH, "rb") as f:
    _JWKSET = JWKSet()
    _JWKSET.import_keyset(f.read())


class AuthenticationException(Exception):
    pass


def authenticate():
    """
    Authenticate the request, this implements authentication via
    token using Authentication header

    Authorization: Bearer <token>

    Valid tokens are defined in a list the config.json file
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header:
        raise AuthenticationException("No Authentication header")

    if not auth_header.startswith("Bearer "):
        raise AuthenticationException(
            "Authentication header must have the format `Bearer <token>`"
        )

    auth_token = auth_header.replace("Bearer ", "")

    auth_jwt = JWT()
    try:
        payload = auth_jwt.deserialize(auth_token, key=_JWKSET)
    except JWException as exc:
        raise AuthenticationException(str(exc)) from exc


def return_exception(exc):
    return Response(str(exc), 500, content_type="text/plain")


@app.route("/upload/", methods=["POST"])
def upload():
    # authenticate the request for starters
    try:
        authenticate()
    except AuthenticationException as exc:
        return json.jsonify({"detail": str(exc)}), 401
    except Exception as exc:
        return json.jsonify({"detail": str(exc)}), 500

    # check if the post request has the file part
    if "file" not in request.files:
        return json.jsonify({"detail": "no file provided"}), 400

    file = request.files["file"]

    content_bytes = BytesIO(file.read())
    content_bytes.seek(0)
    im = Image.open(content_bytes)
    font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf", 15)
    d = ImageDraw.Draw(im)

    now = datetime.utcnow()
    caption = now.strftime("%Y-%m-%d %H:%M")
    d.text(
        (math.floor(im.width) / 2, 20),
        caption,
        fill=(255, 255, 255),
        anchor="ms",
        font=font,
    )

    try:
        im.save(_FILE_UPLOAD_PATH, "JPEG")
    except Exception as exc:
        return json.jsonify({"detail": str(exc)}), 400

    return json.jsonify({"detail": "OK"}), 201


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8887)
