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

2. Clone Xray-Daemon repository and install dependencies:
```bash
git clone https://github.com/mrbaco/Xray-Daemon.git /home/$(whoami)/xray-daemon
sudo apt install python3-venv -y
python3 -m venv /home/$(whoami)/xray-daemon/.venv
/home/$(whoami)/xray-daemon/.venv/bin/python -m pip install -r /home/$(whoami)/xray-daemon/requirements.txt
```

3. Create `.env`-file with content (don't forget to fill in the gaps):
```bash
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

4. Create service `/etc/systemd/system/xray-daemon.service` to serve requests (in this example I use socket):
```bash
printf "[Unit]
Description=Xray REST API daemon to proxy requests
After=multi-user.target

[Service]
Type=idle
User=$(whoami)
ExecStart=/home/$(whoami)/xray-daemon/.venv/bin/python /home/$(whoami)/xray-daemon/main.py
ExecStartPost=/usr/bin/sleep 5
ExecStartPost=chmod 666 /tmp/xray-daemon.sock
Restart=always

[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/xray-daemon.service
```

5. Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable xray-daemon.service
sudo systemctl start xray-daemon.service
```

6. Create self-signed certificate to secure connect to daemon through Nginx:
```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -subj "/CN=your_public_ip_or_hostname" -keyout /etc/ssl/private/nginx-selfsigned.key -out /etc/ssl/certs/nginx-selfsigned.crt -batch
sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
```

7. Add Nginx config:
```
server {
    listen 55000 ssl;

	ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
	ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;

    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
	ssl_prefer_server_ciphers on;
	ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
	ssl_ecdh_curve secp384r1;
	ssl_session_cache shared:SSL:10m;
	ssl_session_tickets off;
	resolver 8.8.8.8 8.8.4.4 valid=300s;
	resolver_timeout 5s;
	add_header X-Frame-Options DENY;
	add_header X-Content-Type-Options nosniff;

	ssl_dhparam /etc/ssl/certs/dhparam.pem;

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_redirect off;
        proxy_buffering off;
        proxy_pass http://xray_daemon;
    }
}

upstream xray_daemon {
	server unix:/tmp/xray-daemon.sock fail_timeout=0;
}
```

8. Restart Nginx:
```bash
sudo systemctl restart nginx.service
```

9. Copy `/etc/ssl/certs/nginx-selfsigned.crt` to client and try to do request:
```bash
curl https://your_public_ip_or_hostname:55000/health --cacert "path/to/nginx-selfsigned.crt"
```