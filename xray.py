import grpc

from typing import Union
from google.protobuf import message as _message
from xray_rpc.app.proxyman.command import (
	command_pb2_grpc as proxyman_command_pb2_grpc,
	command_pb2 as proxyman_command_pb2,
)
from xray_rpc.app.stats.command import (
	command_pb2 as stats_command_pb2,
	command_pb2_grpc as stats_command_pb2_grpc
)
from xray_rpc.common.protocol import user_pb2
from xray_rpc.common.serial import typed_message_pb2
from xray_rpc.proxy.shadowsocks import config_pb2 as shadowsocks_config_pb2
from xray_rpc.proxy.shadowsocks_2022 import config_pb2 as shadowsocks_2022_config_pb2
from xray_rpc.proxy.trojan import config_pb2 as trojan_config_pb2
from xray_rpc.proxy.vless import account_pb2 as vless_account_pb2
from xray_rpc.proxy.vmess import account_pb2 as vmess_account_pb2
from xray_rpc.proxy.socks import config_pb2 as socks_config_pb2

from schemas import NodeTypeEnum, XrayError


def to_typed_message(message: _message):
	return typed_message_pb2.TypedMessage(type=message.DESCRIPTOR.full_name, value=message.SerializeToString())

class Xray(object):
	def __init__(self, api_host: str, api_port: int):
		self.xray_client = grpc.insecure_channel(target=f"{api_host}:{api_port}")

	async def get_user_upload_traffic(self, email: str, reset: bool = False) -> Union[int, XrayError]:
		"""
		Get user upload traffic
		:param email: user e-mail
		:param reset: reset upload traffic
		:return:
		"""
		stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
		try:
			resp = stub.GetStats(
				stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>uplink", reset=reset)
			)
			return resp.stat.value
		except grpc.RpcError as rpc_err:
			detail = rpc_err.details()
			if detail.endswith("uplink not found."):
				return XrayError(detail)
			
			return XrayError(detail)

	async def get_user_download_traffic(self, email: str, reset: bool = False) -> Union[int, XrayError]:
		"""
		Get user download traffic
		:param email: user e-mail
		:param reset: reset download traffic
		:return:
		"""
		stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
		try:
			resp = stub.GetStats(
				stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>downlink", reset=reset)
			)
			return resp.stat.value
		except grpc.RpcError as rpc_err:
			detail = rpc_err.details()
			if detail.endswith("downlink not found."):
				return XrayError(detail)
			
			return XrayError(detail)

	async def get_inbound_upload_traffic(self, inbound_tag: str, reset: bool = False) -> Union[int, XrayError]:
		"""
		Get inbound upload traffic
		:param inbound_tag: inbound tag
		:return:
		"""
		stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
		try:
			resp = stub.GetStats(
				stats_command_pb2.GetStatsRequest(name=f"inbound>>>{inbound_tag}>>>traffic>>>uplink", reset=reset)
			)
			return resp.stat.value
		except grpc.RpcError as rpc_err:
			return XrayError(rpc_err.details())

	async def get_inbound_download_traffic(self, inbound_tag: str, reset: bool = False) -> Union[int, XrayError]:
		"""
		Get inbound download traffic
		:param inbound_tag: inbound tag
		:return:
		"""
		stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
		try:
			resp = stub.GetStats(
				stats_command_pb2.GetStatsRequest(name=f"inbound>>>{inbound_tag}>>>traffic>>>downlink", reset=reset)
			)
			return resp.stat.value
		except grpc.RpcError as rpc_err:
			return XrayError(rpc_err.details())

	async def add_user(
		self,
		inbound_tag: str,
		email: str,
		level: int,
		type: str,
		password: str = "",
		cipher_type: int = 0,
		uuid: str = "",
		flow: str = "xtls-rprx-direct",
	) -> Union[None, XrayError]:
		"""
		Add user to inbound
		:param inbound_tag:
		:param email:
		:param level:
		:param type:
		:param password:
		:param cipher_type:
		:param uuid:
		:param flow:
		:return:
		"""
		stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
		try:
			if type == NodeTypeEnum.VMess.value:
				user = user_pb2.User(
					email=email,
					level=level,
					account=to_typed_message(vmess_account_pb2.Account(id=uuid)),
				)
			elif type == NodeTypeEnum.VLess.value:
				user = user_pb2.User(
					email=email,
					level=level,
					account=to_typed_message(vless_account_pb2.Account(id=uuid, flow=flow)),
				)
			elif type == NodeTypeEnum.Shadowsocks.value:
				try:
					stub.AlterInbound(
						proxyman_command_pb2.AlterInboundRequest(
							tag=inbound_tag,
							operation=to_typed_message(proxyman_command_pb2.RemoveUserOperation(email=email)),
						)
					)
				except grpc.RpcError as _:
					pass

				user = user_pb2.User(
					email=email,
					level=level,
					account=to_typed_message(
						shadowsocks_config_pb2.Account(password=password, cipher_type=cipher_type)
					),
				)
			elif type == NodeTypeEnum.Trojan.value:
				user = user_pb2.User(
					email=email,
					level=level,
					account=to_typed_message(trojan_config_pb2.Account(password=password, flow=flow)),
				)
			elif type == NodeTypeEnum.Socks.value:
				user = user_pb2.User(
					email=email,
					level=level,
					account=to_typed_message(socks_config_pb2.Account(username=email, password=password)),
				)
			else:
				return XrayError(f"{type} not found")
			
			stub.AlterInbound(
				proxyman_command_pb2.AlterInboundRequest(
					tag=inbound_tag,
					operation=to_typed_message(proxyman_command_pb2.AddUserOperation(user=user)),
				)
			)
		except grpc.RpcError as rpc_err:
			detail = rpc_err.details()

			if detail.endswith(f"User {email} already exists."):
				return XrayError(detail)
			elif detail.endswith(f"handler not found: {inbound_tag}"):
				return XrayError(detail)
			else:
				return XrayError(detail)

	async def remove_user(self, inbound_tag: str, email: str):
		"""
		Remove user from inbound
		:param inbound_tag:
		:param email:
		:return:
		"""
		stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
		try:
			stub.AlterInbound(
				proxyman_command_pb2.AlterInboundRequest(
					tag=inbound_tag, operation=to_typed_message(proxyman_command_pb2.RemoveUserOperation(email=email))
				)
			)
		except grpc.RpcError as rpc_err:
			detail = rpc_err.details()
			if detail.endswith(f"User {email} already exists."):
				return XrayError(detail)
			elif detail.endswith(f"handler not found: {inbound_tag}"):
				return XrayError(detail)
			else:
				return XrayError(detail)
