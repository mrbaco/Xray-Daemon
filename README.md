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
DAEMON_LOG=xray_daemon.log
DATABASE_FILE=
```

