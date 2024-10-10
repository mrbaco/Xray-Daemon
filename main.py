import os
import logging
import json
import asyncio

from dotenv import load_dotenv
from aiohttp import web, ContentTypeError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from pathlib import Path

from xray import Xray
from consts import XrayError

load_dotenv()

# init logger
logging.basicConfig(
	filename=os.getenv("DAEMON_LOG"),
	level=logging.INFO,
	format="%(asctime)s %(levelname)s %(message)s"
)

# create instance of Xray-class and connect to it Xray by GRPC
xray = Xray(
	os.getenv("GRPC_URL"),
	int(os.getenv("GRPC_PORT"))
)

logger = logging.getLogger(__name__)
secret = os.getenv("SECRET")
routes = web.RouteTableDef()

# read database
database = {}
if Path(os.getenv("DATABASE_FILE")).is_file():
	with open(os.getenv("DATABASE_FILE")) as f:
		database = json.load(f)

def dump_database():
	"""
	Dump database variable to file
	"""
	with open(os.getenv("DATABASE_FILE"), "w") as f:
		json.dump(database, f, indent=4)

def error_response(
	message: str,
	status: int = 400,
	code: int = 0,
	reason: str = "Bad Request"
) -> Response:
	"""
	Create error response
	:param message:
	:param status:
	:param code:
	:param reason:
	:return:
	"""
	logger.info(f"{status} - {message}")
	return web.json_response({"message": message, "code": code}, status=status, reason=reason)


@routes.post(f"/{secret}/user")
async def create_user(request: Request):
	"""
	Add user to inbound.

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
		  limit:
			type: integer
			format: int64
	responses:
	  201:
		description: user was created
	  404:
		description: inbound not found
		schema:
		  type: object
		  properties:
			message:
			  type: string
			code:
			  type: integer
			  format: int32
	  400:
		description: user already exist OR json parse error OR inbound_tag is required OR email is required OR level is required OR type is required
		schema:
		  type: object
		  properties:
			message:
			  type: string
			code:
			  type: integer
			  format: int32
	  500:
		description: Xray error
		schema:
		  type: object
		  properties:
			message:
			  type: string
			code:
			  type: integer
			  format: int32
	"""
	# Validate request
	try:
		data = await request.json()

		if not "inbound_tag" in data:
			return error_response("inbound_tag is required")
			
		if not "email" in data:
			return error_response("email is required")
			
		if not "level" in data:
			return error_response("level is required")
		else:
			data['level'] = int(data['level'])
			
		if not "type" in data:
			return error_response("type is required")
		
		if "cipher_type" in data:
			data['cipher_type'] = int(data['cipher_type'])
		
		if "alter_id" in data:
			data['alter_id'] = int(data['alter_id'])
		
		if "limit" in data:
			data['limit'] = int(data['limit'])

			if data['limit'] < 0:
				data['limit'] = 0
			
	except (ContentTypeError, ValueError) as e:
		return error_response("error in JSON parsing")
	
	# execure user creation
	result = await xray.add_user(
		inbound_tag=data['inbound_tag'],
		email=data['email'],
		level=data['level'],
		type=data['type'],
		password=data.get("password", ""),
		cipher_type=data.get("cipher_type", 0),
		uuid=data.get("uuid", ""),
		alter_id=data.get("alter_id", 0),
		flow=data.get("flow", "xtls-rprx-direct"),
	)

	if type(result) is XrayError:
		return error_response(result.message, 500, result.code, "Internal Server Error")
	
	# create inbound_tag in database if not exists
	if not data['inbound_tag'] in database:
		database.update({data['inbound_tag']: []})
	
	# add user to inbound and dump database
	data.update({
		"traffic": 0,
		"active": True
	})
	
	database['inbound_tag'].append(data)
	dump_database()

	logger.info(f"create new user {data['email']} for inbound {data['inbound_tag']}")
	
	return web.Response(status=201)


@routes.get(f"/{secret}/user/{{inbound_tag}}/{{email}}")
async def get_user(request: Request):
	"""
	Get user from inbound.

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
			message:
			  type: string
			code:
			  type: integer
			  format: int32
	"""
	inbound_tag = request.match_info.get("inbound_tag")
	email = request.match_info.get("email")

	if not inbound_tag in database:
		return error_response("inbound was not found", 404)
	
	user = next(filter(lambda user : user['email'] == email, database[inbound_tag]), None)

	if user == None:
		return error_response("user was not found", 404)
	
	return web.json_response(user)

@routes.delete(f"/{secret}/user/{{inbound_tag}}/{{email}}")
async def delete_user(request: Request):
	"""
	Remove user from inbound.

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
			message:
			  type: string
			code:
			  type: integer
			  format: int32
	  500:
		description: Xray error
		schema:
		  type: object
		  properties:
			message:
			  type: string
			code:
			  type: integer
			  format: int32
	"""
	inbound_tag = request.match_info.get("inbound_tag")
	email = request.match_info.get("email")

	if not inbound_tag in database:
		return error_response("inbound was not found", 404)
	
	user = next(filter(lambda user : user['email'] == email, database[inbound_tag]), None)

	if user == None:
		return error_response("user was not found", 404)
	
	result = xray.remove_user(inbound_tag, email)

	if type(result) is XrayError:
		return error_response(result.message, 500, result.code, "Internal Server Error")
	
	database[inbound_tag][:] = [d for d in database[inbound_tag] if d['email'] != email]
	dump_database()

	return web.Response(status=204)


@routes.get(f"/{secret}/stats")
async def get_stats(request: Request):
	"""
	Get server statistic.

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
			message:
			  type: string
			code:
			  type: integer
			  format: int32
	"""
	result = []

	for inbound_tag in database:
		download_traffic = xray.get_inbound_download_traffic(inbound_tag)

		if type(download_traffic) is XrayError:
			return error_response(
				download_traffic.message,
				500,
				download_traffic.code,
				"Internal Server Error"
			)

		upload_traffic = xray.get_inbound_upload_traffic(inbound_tag)

		if type(upload_traffic) is XrayError:
			return error_response(
				upload_traffic.message,
				500,
				upload_traffic.code,
				"Internal Server Error"
			)
		
		result.append({
			"inbound_tag": inbound_tag,
			"download_traffic": download_traffic,
			"upload_traffic": upload_traffic
		})
	
	return web.json_response(result)

@routes.post(f"/{secret}/routine")
async def start_routine(request: Request):
	"""
	Run routine operations (update user traffic, 
		control limits and block users).

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
			message:
			  type: string
	"""
	# iterate users
	for inbound_tag in database:
		for user in database[inbound_tag]:
			download_traffic = xray.get_user_download_traffic(user['email'])

			if type(download_traffic) is XrayError:
				return error_response(
					download_traffic.message,
					500,
					download_traffic.code,
					"Internal Server Error"
				)

			upload_traffic = xray.get_user_upload_traffic(user['email'])

			if type(upload_traffic) is XrayError:
				return error_response(
					upload_traffic.message,
					500,
					upload_traffic.code,
					"Internal Server Error"
				)
			
			# update traffic
			user['traffic'] = download_traffic + upload_traffic

			# compare traffic and limits
			if user['limit'] != 0 and user['traffic'] >= user['limit']:
				user['active'] = False

				# remove user
				result = xray.remove_user(inbound_tag, user['email'])

				if type(result) is XrayError:
					return error_response(result.message, 500, result.code, "Internal Server Error")
				
				database[inbound_tag][:] = [d for d in database[inbound_tag] if d['email'] != user['email']]
	
	dump_database()

	return web.Response(status=204)


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
	return web.json_response(
		{
			"status": "working"
		},
		status=418,
		reason="I am a vacuum cleaner"
	)

async def push_database():
	# add users from database to Xray
	for inbound_tag in database:
		for user in database[inbound_tag]:
			if user.get("active", False) == True:
				result = await xray.add_user(
					inbound_tag=inbound_tag,
					email=user['email'],
					level=user['level'],
					type=user['type'],
					password=user.get("password", ""),
					cipher_type=user.get("cipher_type", 0),
					uuid=user.get("uuid", ""),
					alter_id=user.get("alter_id", 0),
					flow=user.get("flow", "xtls-rprx-direct"),
				)

				if type(result) is XrayError:
					logger.error(result.message)

if __name__ == "__main__":
	asyncio.run(push_database())

	# start daemon
	app = web.Application()
	app.add_routes(routes)

	web.run_app(
		app,
		host=os.getenv("DAEMON_HOST"),
		port=int(os.getenv("DAEMON_PORT"))
	)
