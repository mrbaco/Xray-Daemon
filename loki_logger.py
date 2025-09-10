from fastapi import Request, status
from fastapi.concurrency import iterate_in_threadpool
from fastapi.responses import JSONResponse
from logging_loki import LokiHandler
from dotenv import load_dotenv

import re, os, logging, time


load_dotenv('.env')

def configure_logger(service: str) -> logging.Logger:
    logger = logging.getLogger('fastapi')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    loki_handler = LokiHandler(
        url=f"{os.getenv('LOKI_URL')}/loki/api/v1/push",
        auth=(os.getenv('LOKI_LOGIN'), os.getenv('LOKI_PASSWORD')),
        tags={'service': service, 'env': os.getenv('ENV')},
        version='1',
    )
    loki_handler.setFormatter(formatter)
    logger.addHandler(loki_handler)

    return logger

LOGGER = configure_logger('xray-daemon')

class Logger:
    def __init__(self, logger: logging.Logger, req_body_required: bool = False, resp_body_required: bool = False) -> None:
        self.logger = logger
        self.req_body_required = req_body_required
        self.resp_body_required = resp_body_required

        self.patterns = {
            'password': re.compile(r'(password":\s*")[^"]*(")', re.IGNORECASE),
            'token': re.compile(r'(token":\s*")[^"]*(")', re.IGNORECASE),
            'api_key': re.compile(r'(api_key":\s*")[^"]*(")|(api[_-]key[=:])[^&\s]*', re.IGNORECASE)
        }

    async def __call__(self, request: Request, call_next) -> None:
        try:
            req_body = await request.body()
            try:
                req_body = req_body.decode()
                for _, pattern in self.patterns.items():
                    req_body = pattern.sub(r'\1*****\2', req_body)
            except:
                req_body = req_body
                self.req_body_required = False

            self.logger.info(
                'IN',
                extra={
                    'tags': {
                        'method': request.method,
                        'path': request.url.path,
                        'body': req_body if self.req_body_required else None,
                        'length': len(req_body),
                        'query': dict(request.query_params),
                        'ip': request.client.host,
                    }
                },
            )

            start_time = time.time()
            response = await call_next(request)

            resp_body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(resp_body))

            try:
                resp_body = b''.join(resp_body).decode()
                resp_body = resp_body.translate(str.maketrans({
                    "-":  r"\-",
                    "]":  r"\]",
                    "\\": r"\\",
                    "^":  r"\^",
                    "$":  r"\$",
                    "*":  r"\*",
                    ".":  r"\."
                }))
            except:
                resp_body = resp_body
                self.resp_body_required = False

            process_time = (time.time() - start_time) * 1000
            
            self.logger.info(
                'OUT',
                extra={
                    'tags': {
                        'method': request.method,
                        'path': request.url.path,
                        'body': resp_body[:1024] if self.resp_body_required else None,
                        'length': len(resp_body),
                        'status_code': response.status_code,
                        'process_time_ms': process_time,
                    }
                },
            )
            
            return response

        except Exception as e:
            self.logger.error(
                'ERROR',
                extra={
                    'tags': {
                        'error_type': type(e).__name__,
                        'error_msg': str(e),
                        'method': request.method,
                        'path': request.url.path,
                    }
                },
                exc_info=True,
            )

            return JSONResponse({"message": type(e).__name__}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
