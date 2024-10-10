import os
import logging
import json

from dotenv import load_dotenv
from aiohttp import web
from aiohttp.web_request import Request
from pathlib import Path

from xray import Xray

load_dotenv()

logging.basicConfig(filename=os.getenv("DAEMON_LOG"), level=logging.INFO)

xray = Xray(
    os.getenv("GRPC_URL"),
    int(os.getenv("GRPC_PORT"))
)

logger = logging.getLogger(__name__)
secret = os.getenv("SECRET")
routes = web.RouteTableDef()

database = {}
if Path(os.getenv("DATABASE_FILE")).is_file():
    with open(os.getenv("DATABASE_FILE")) as f:
        database = json.load(f)
        f.close()

@routes.post(f"/{secret}/user")
async def create_user(request: Request):
    """
    Add user to inbound

    ---
    tags:
    - User
    produces:
    - application/json
    parameters:
    - in: body
      name: body
      description: User data
      required: true
      schema:
        type: object
        properties:
          inbound_tag:
            type: string
            required: true
          email:
            type: string
            required: true
          level:
            type: integer
            format: int32
          type:
            type: string
          password:
            type: string
          cipher_type:
            type: integer
            format: int32
          uuid:
            type: string
          alter_id:
            type: integer
            format: int32
          flow:
            type: string
    responses:
      201:
        description: user was created
      404:
        description: inbound not found
        schema:
          type: object
          properties:
            error:
              type: string
      400:
        description: user already exist
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Xray error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    
    pass

@routes.get(f"/{secret}/user/{{inbound_tag}}/{{email}}")
async def get_user(request: Request):
    """
    Get user from inbound

    ---
    tags:
    - User
    produces:
    - application/json
    parameters:
    - name: inbound_tag
      in: path
      type: string
      required: true
      description: inbound tag
    - name: email
      in: path
      type: string
      required: true
      description: user e-mail
    responses:
      200:
        description: user was found
        schema:
          type: object
          properties:
            inbound_tag:
              type: string
              required: true
            email:
              type: string
              required: true
            level:
              type: integer
              format: int32
            type:
              type: string
            password:
              type: string
            cipher_type:
              type: integer
              format: int32
            uuid:
              type: string
            alter_id:
              type: integer
              format: int32
            flow:
              type: string
            traffic:
              type: integer
              format: int64
            limit:
              type: integer
              format: int64
            active:
              type: boolean
      404:
        description: inbound or user was not found
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Xray error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    pass

@routes.delete(f"/{secret}/user/{{inbound_tag}}/{{email}}")
async def delete_user(request: Request):
    """
    Remove user from inbound

    ---
    tags:
    - User
    produces:
    - application/json
    parameters:
    - name: inbound_tag
      in: path
      type: string
      required: true
      description: inbound tag
    - name: email
      in: path
      type: string
      required: true
      description: user e-mail
    responses:
      204:
        description: user was deleted
      404:
        description: inbound or user not found
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Xray error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    pass

@routes.get(f"/{secret}/stats")
async def get_stats(request: Request):
    """
    Get server statistic

    ---
    tags:
    - Stats
    produces:
    - application/json
    responses:
      200:
        description: ok
        schema:
          type: object
          properties:
            inbounds:
              type: array
              items:
                type: object
                properties:
                  inbound_tag:
                    type: string
                  download_traffic:
                    type: integer
                    format: int64
                  upload_traffic:
                    type: integer
                    format: int64
      500:
        description: Xray error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    pass

@routes.post(f"/{secret}/routine")
async def start_routine(request: Request):
    """
    Run routine operations

    ---
    tags:
    - Routine
    produces:
    - application/json
    responses:
      204:
        description: operations were done
      500:
        description: Xray error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    pass

@routes.get(f"/health")
async def health_check(_: Request):
    """
    Check daemon/server availability

    ---
    tags:
    - Availability
    produces:
    - application/json
    responses:
      418:
        description: everything is good
    """
    response = web.json_response({"status": "working"})
    response.set_status(418, "I am a vacuum cleaner")

    return response

if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)

    web.run_app(
        app,
        host=os.getenv("DAEMON_HOST"),
        port=int(os.getenv("DAEMON_PORT"))
    )
