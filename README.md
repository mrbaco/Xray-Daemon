# Xray REST API daemon

Daemon controls users of Xray server by REST API. Xray GRPC class was forked from https://github.com/laoshan-tech/xray-node

## Installation

1. Add new item in your config to serve GRPC (don't forget to restart Xray after that):
```json
	"api": {
		"tag": "api",
		"listen": "127.0.0.1:8000",
		"services": [
			"HandlerService",
			"RoutingService",
			"StatsService"
		]
	}
```

2. Create `.env`-file with content (don't forget to fill in the gaps):
```
GRPC_URL=127.0.0.1
GRPC_PORT=8000
DAEMON_HOST=127.0.0.1
DAEMON_PORT=123
SECRET=
DAEMON_LOG=
DAEMON_LOG_FORMAT=%(asctime)s %(levelname)s %(message)s
DATABASE_FILE=
DATE_TIME_FORMAT=%d.%m.%Y %H:%M:%S
RESET_TRAFFIC_PERIOD=2635200
```

You're free to use `DAEMON_SOCKET_PATH` instead of `DAEMON_HOST` and `DAEMON_PORT` to serve requests using unix socket.