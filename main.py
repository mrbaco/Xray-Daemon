import os
import logging
import json
import asyncio
import uuid
import secrets

from dotenv import load_dotenv
from aiohttp import web, ContentTypeError
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from pathlib import Path
from time import gmtime, strftime, strptime, mktime
from typing import Union

from xray import Xray
from consts import XrayError, NodeTypeEnum, CIPHER_TYPE

load_dotenv()

# init logger
logging.basicConfig(
	filename=os.getenv("DAEMON_LOG"),
	level=logging.INFO,
	format=os.getenv("DAEMON_LOG_FORMAT")
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


def get_today() -> str:
	return strftime(os.getenv("DATE_TIME_FORMAT"), gmtime())

def dump_database():
	"""
	Dump database variable to file
	"""
	with open(os.getenv("DATABASE_FILE"), "w") as f:
		json.dump(database, f, indent=4)

def error_response(
	message: str,
	status: int = 400,
	code: int = 0
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
	return web.json_response({"message": message, "code": code}, status=status)

async def add_user(inbound_tag: str, user: dict) -> Union[int, XrayError]:
	return await xray.add_user(
		inbound_tag=inbound_tag,
		email=user['email'],
		level=user['level'],
		type=user['type'],
		password=user.get("password", ""),
		cipher_type=CIPHER_TYPE[user.get("cipher_type", "unknown")],
		uuid=user.get("uuid", ""),
		alter_id=user.get("alter_id", 0),
		flow=user.get("flow", "xtls-rprx-direct"),
	)

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
		schema:
		  type: object
		  properties:
			uuid:
			  type: string
			password:
			  type: string
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
		description: user already exist OR validation error OR 
			inbound_tag is required OR email is required OR level is required OR 
			type is required OR valid cipher_type is required
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
	response = {}

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
		
		if "cipher_type" in data and not data['cipher_type'] in CIPHER_TYPE:
			return error_response("valid cipher_type is required")
		
		if "alter_id" in data:
			data['alter_id'] = int(data['alter_id'])
		
		if "limit" in data:
			data['limit'] = int(data['limit'])

			if data['limit'] < 0:
				data['limit'] = 0
		
		if data['type']  == NodeTypeEnum.VMess.value or data['type'] == NodeTypeEnum.VLess.value:
			data['uuid'] = str(uuid.uuid4())
			response = {"uuid": data['uuid']}
		else:
			if data['cipher_type'] == "2022-blake3-aes-128-gcm":
				data['password'] = secrets.token_urlsafe(16)
			else:
				data['password'] = secrets.token_urlsafe(32)

			response = {"password": data['password']}
			
	except (ContentTypeError, ValueError) as _:
		return error_response("validation error")
	
	# execute user creation
	result = await add_user(data['inbound_tag'], data)

	if type(result) is XrayError:
		return error_response(result.message, 500, result.code, "Internal Server Error")
	
	# create inbound_tag in database if not exists
	if not data['inbound_tag'] in database:
		database.update({data['inbound_tag']: []})
	
	# add user to inbound and dump database
	date = get_today()

	data.update({
		"traffic": 0,
		"active": True,
		"creation_date": date,
		"reset_traffic_date": date
	})
	
	database['inbound_tag'].append(data)

	dump_database()

	logger.info(f"create new user {data['email']} for inbound {data['inbound_tag']}")
	
	return web.json_response(response, status=201)


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
			creation_date:
			  type: string
			reset_traffic_date:
			  type: string
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
	
	logger.info(f"user {inbound_tag}/{email} info was requested")
	
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
	
	result = await xray.remove_user(inbound_tag, email)

	if type(result) is XrayError:
		return error_response(result.message, 500, result.code, "Internal Server Error")
	
	database[inbound_tag][:] = [d for d in database[inbound_tag] if d['email'] != email]
	dump_database()

	logger.info(f"user {inbound_tag}/{email} was fully deleted")

	return web.Response(status=204)


@routes.put(f"/{secret}/user/{{inbound_tag}}/{{email}}")
async def update_user(request: Request):
	"""
	Update user.

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
	- in: body
	  name: body
	  description: User data
	  required: true
	  schema:
		type: object
		properties:
		  active:
			type: boolean
		  limit:
			type: integer
			format: int64
	responses:
	  204:
		description: user was updated
	  400:
		description: validation error
		schema:
		  type: object
		  properties:
			message:
			  type: string
			code:
			  type: integer
			  format: int32
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

	try:
		data = await request.json()

		if "limit" in data:
			data['limit'] = int(data['limit'])

			if data['limit'] < 0:
				data['limit'] = 0

			user['limit'] = data['limit']
		
		if "active" in data:
			if data['active'] != True:
				data['active'] == False

			user['active'] = data['active']

	except (ContentTypeError, ValueError) as _:
		return error_response("validation error")

	dump_database()

	return web.Response(status=204)


@routes.get(f"/{secret}/stats")
async def get_stats(_: Request):
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
		download_traffic = await xray.get_inbound_download_traffic(inbound_tag)
		upload_traffic = await xray.get_inbound_upload_traffic(inbound_tag)

		if type(download_traffic) is XrayError or type(upload_traffic) is XrayError:
			if type(download_traffic) is XrayError:
				error = download_traffic
			else:
				error = upload_traffic

			return error_response(
				error.message,
				500,
				error.code,
				"Internal Server Error"
			)
		
		result.append({
			"inbound_tag": inbound_tag,
			"download_traffic": download_traffic,
			"upload_traffic": upload_traffic
		})
	
	logger.info(f"server stats were requested")

	return web.json_response(result)


@routes.post(f"/{secret}/routine")
async def start_routine(_: Request):
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
			# update traffic
			download_traffic = await xray.get_user_download_traffic(user['email'])
			upload_traffic = await xray.get_user_upload_traffic(user['email'])

			if type(download_traffic) is XrayError or type(upload_traffic) is XrayError:
				if type(download_traffic) is XrayError:
					error = download_traffic
				else:
					error = upload_traffic

				return error_response(
					error.message,
					500,
					error.code,
					"Internal Server Error"
				)
			
			user['traffic'] = download_traffic + upload_traffic

			# compare traffic and limit then set inactive due traffic overage
			if (
				user['limit'] != 0 and 
	   			user['traffic'] >= user['limit'] and
				user['active'] == True
			):
				user['active'] = False

				# remove user
				result = await xray.remove_user(inbound_tag, user['email'])

				if type(result) is XrayError:
					return error_response(result.message, 500, result.code, "Internal Server Error")
				
				logger.info(f"block user {inbound_tag}/{user['email']} due traffic overage")
			
			# reset traffic after reset period
			if user['active'] == False:
				using_period = mktime(gmtime) - mktime(strptime(user['reset_traffic_date'], os.getenv("DATE_TIME_FORMAT")))

				if using_period >= os.getenv("RESET_TRAFFIC_PERIOD"):
					user['active'] = True
					user['traffic'] = 0
					user['reset_traffic_date'] = get_today()

					# restore user
					result = await add_user(inbound_tag, user)

					if type(result) is XrayError:
						return error_response(result.message, 500, result.code, "Internal Server Error")
					
					logger.info(f"restore user {inbound_tag}/{user['email']} after reset traffic period")
	
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
	return web.json_response({"status": "working"}, status=418, reason="I am a vacuum cleaner")


async def push_database():
	# add active users from database to Xray
	for inbound_tag in database:
		for user in database[inbound_tag]:
			if user.get("active", False) == True:
				result = await add_user(inbound_tag, user)

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
