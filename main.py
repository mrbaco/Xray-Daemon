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

load_dotenv(override=True)

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
		flow=user.get("flow", "xtls-rprx-direct"),
	)

async def create_user(request: Request):
	"""
	Add user to inbound.

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
	- in: body
	  name: body
	  description: User data
	  required: true
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
		  cipher_type:
			type: string
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

	inbound_tag = request.match_info.get("inbound_tag")

	# Validate JSON-body
	try:
		data = await request.json()
			
		if not "email" in data:
			return error_response("email is required", code=11)
			
		if not "type" in data:
			return error_response("type is required", code=12)
		
		if "cipher_type" in data and not data['cipher_type'] in CIPHER_TYPE:
			return error_response("valid cipher_type is required", code=13)
		
		data['limit'] = int(data.get("limit", 0))

		if data['limit'] < 0:
			data['limit'] = 0
		
		if data['type']  == NodeTypeEnum.VMess.value or data['type'] == NodeTypeEnum.VLess.value:
			data['uuid'] = str(uuid.uuid4())
			response = {"uuid": data['uuid']}
		else:
			if data.get("cipher_type") == "2022-blake3-aes-128-gcm":
				data['password'] = secrets.token_urlsafe(64)[0:24]
			elif data.get("cipher_type") == "2022-blake3-aes-256-gcm":
				data['password'] = secrets.token_urlsafe(64)[0:44]
			else:
				data['password'] = secrets.token_urlsafe(64)[0:22]

			response = {"password": data['password']}

		if data['type'] == NodeTypeEnum.Shadowsocks_2022.value:
			del data['cipher_type']
		
		data['level'] = int(data.get("level", 0))
			
	except (ContentTypeError, ValueError) as _:
		return error_response("validation error", code=14)

	# check if user exists
	if inbound_tag in database:
		user = next(filter(lambda user : user['email'] == data['email'], database[inbound_tag]), None)

		if user != None:
			return error_response("user already exist in database", code=15)
	
	# execute user creation
	result = await add_user(inbound_tag, data)

	if type(result) is XrayError:
		return error_response(result.message, 500, result.code)
	
	# create inbound_tag in database if not exist
	if not inbound_tag in database:
		database.update({inbound_tag: []})
	
	# add user to inbound and dump database
	date = get_today()

	data.update({
		"traffic": 0,
		"active": True,
		"blocked": False,
		"creation_date": date,
		"reset_traffic_date": date
	})
	
	database[inbound_tag].append(data)

	dump_database()

	logger.info(f"create new user {data['email']} for inbound {inbound_tag}")
	
	return web.json_response(response, status=201)

async def get_users(request: Request):
	"""
	Get all users from inbound.

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
	responses:
	  200:
		description: users were found
		schema:
		  type: array
		  items:
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
			  blocked:
			    type: boolean
			  creation_date:
			    type: string
			  reset_traffic_date:
			    type: string
	  404:
		description: inbound was not found
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

	if not inbound_tag in database:
		return error_response("inbound was not found", 404, 21)
	
	return web.json_response(database[inbound_tag])

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
			blocked:
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
		return error_response("inbound was not found", 404, 31)

	user = next(filter(lambda user : user['email'] == email, database[inbound_tag]), None)

	if user == None:
		return error_response("user was not found", 404, 32)

	logger.info(f"user {inbound_tag}/{email} info was requested")
	
	return web.json_response(user)

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
		return error_response("inbound was not found", 404, 41)
	
	user = next(filter(lambda user : user['email'] == email, database[inbound_tag]), None)

	if user == None:
		return error_response("user was not found", 404, 42)
	
	result = await xray.remove_user(inbound_tag, email)

	if type(result) is XrayError:
		return error_response(result.message, 500, result.code)
	
	database[inbound_tag][:] = [d for d in database[inbound_tag] if d['email'] != email]
	dump_database()

	logger.info(f"user {inbound_tag}/{email} was fully deleted")

	return web.Response(status=204)

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
		  limit:
			type: integer
			format: int64
		  blocked:
		    type: boolean
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
		return error_response("inbound was not found", 404, 51)
	
	user = next(filter(lambda user : user['email'] == email, database[inbound_tag]), None)

	if user == None:
		return error_response("user was not found", 404, 52)

	try:
		data = await request.json()

		if not "limit" in data and not "blocked" in data:
			return error_response("limit or blocked are required", code=53)
		
	except (ContentTypeError, ValueError) as _:
		return error_response("validation error", code=54)
	
	if "limit" in data:
		user['limit'] = int(data['limit'])

		if user['limit'] < 0:
			user['limit'] = 0
	
	if "blocked" in data:
		user['blocked'] = bool(data.get("blocked", True))

		if user['blocked'] == True:
			logger.info(f"block user {inbound_tag}/{user['email']} (still in the queue)")

	dump_database()

	return web.Response(status=204)

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

			return error_response(error.message, 500, error.code)
		
		result.append({
			"inbound_tag": inbound_tag,
			"download_traffic": download_traffic,
			"upload_traffic": upload_traffic
		})
	
	logger.info(f"server stats were requested")

	return web.json_response(result)

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
			active = user['active']

			# update traffic
			download_traffic = await xray.get_user_download_traffic(user['email'])
			upload_traffic = await xray.get_user_upload_traffic(user['email'])

			# block previously blocked user
			if (
				user['active'] == True and
				user['blocked'] == True
			):
				user['active'] = False

			# compare traffic and limit then set inactive due traffic overage
			if not type(download_traffic) is XrayError and not type(upload_traffic) is XrayError:
				user['traffic'] = download_traffic + upload_traffic

				if (
					user['limit'] != 0 and
					user['traffic'] > user['limit'] and
					user['active'] == True
				):
					user['active'] = False

			# remove user
			if user['active'] != active:
				result = await xray.remove_user(inbound_tag, user['email'])

				if type(result) is XrayError:
					logger.error(f"{result.code} {result.message}")
				else:					
					logger.info(f"block user {inbound_tag}/{user['email']}")

			# move reset traffic date to now for blocked users cause not traffic overage
			if (
				user['active'] == False and 
				user['blocked'] == True
			):
				user['reset_traffic_date'] = strftime(
					os.getenv("DATE_TIME_FORMAT"),
					gmtime(mktime(gmtime()) - float(os.getenv("RESET_TRAFFIC_PERIOD")))
				)
			
			# reset traffic after reset period for traffic overage users
			if (
				user['active'] == False and
				user['blocked'] == False
			):
				using_period = mktime(gmtime()) - mktime(strptime(user['reset_traffic_date'], os.getenv("DATE_TIME_FORMAT")))

				if (
					using_period >= float(os.getenv("RESET_TRAFFIC_PERIOD")) or
					user['traffic'] <= user['limit']
				):
					user['active'] = True
					user['traffic'] = 0
					user['reset_traffic_date'] = get_today()

					# restore user
					add_user_result = await add_user(inbound_tag, user)

					# reset user traffic
					reset_dtraffic_result = await xray.get_user_download_traffic(user['email'], True)
					reset_utraffic_result = await xray.get_user_upload_traffic(user['email'], True)

					if type(add_user_result) is XrayError:
						logger.error(f"{add_user_result.code} {add_user_result.message}")
						continue

					if type(reset_dtraffic_result) is XrayError:
						logger.error(f"{reset_dtraffic_result.code} {reset_dtraffic_result.message}")
						continue

					if type(reset_utraffic_result) is XrayError:
						logger.error(f"{reset_utraffic_result.code} {reset_utraffic_result.message}")
						continue
					
					logger.info(f"restore user {inbound_tag}/{user['email']} after reset traffic period")
	
	dump_database()

	return web.Response(status=204)

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

	app.add_routes([
		web.post(f"/{secret}/users/{{inbound_tag}}", create_user),
		web.get(f"/{secret}/users/{{inbound_tag}}", get_users),
		web.get(f"/{secret}/users/{{inbound_tag}}/{{email}}", get_user),
		web.delete(f"/{secret}/users/{{inbound_tag}}/{{email}}", delete_user),
		web.put(f"/{secret}/users/{{inbound_tag}}/{{email}}", update_user),
		web.get(f"/{secret}/stats", get_stats),
		web.post(f"/{secret}/routine", start_routine),
		web.get(f"/health", health_check),
	])

	if os.getenv("DAEMON_SOCKET_PATH") == None:
		web.run_app(
			app,
			host=os.getenv("DAEMON_HOST"),
			port=int(os.getenv("DAEMON_PORT"))
		)
	else:
		web.run_app(
			app,
			path=os.getenv("DAEMON_SOCKET_PATH")
		)
