#!/usr/bin/env python

import os
import multiprocessing

bind = '127.0.0.1:18080' # 指定监听的地址和端口，nginx转发到这里
backlog = 1024 # 服务器中排队等待的最大连接数，建议值64-2048，超过时客户端连接会得到一个error
# workers = multiprocessing.cpu_count() + 1 # 用于处理工作的进程数，这里用建议值
workers = 1
# worker_class = 'gthread' # worker进程的工作方式，有sync,eventlet,gevent,tornado,gthread, 缺省值sync，django用gthread好一些
# worker_connections = 1000 # 最大客户端并发数量，默认情况下是1000
# threads = int(48/workers) # 数据库连接数=workers*threads*2
timeout = 60 # 访问超时时间，默认30s
graceful_timeout = 3 # 接收到restart信号后，worker可在该时间内，继续处理当前任务
keepalive = 2 # server端保持连接时间，默认是2，一般在1-5之间
limit_request_line = 4096 # 请求行的最大大小，范围是0-8192
limit_request_fields = 100 # 请求头字段的数量
limit_request_field_size = 8190*4 # 请求头的大小

reload = False # 代码更新时不重启项目
daemon = False # 是否为守护进程
pidfile = '/tmp/gunicorn.pid' # pid文件名

accesslog = '/tmp/gunicorn_access.log' # 访问日志文件路径，'-'表示输出到终端
access_log_format = '%(t)s %(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(L)s"' # 访问日志文件格式
errorlog = '/tmp/gunicorn_error.log'
loglevel = 'warning'

# pythonpath = '/home/kali/.venv/bin/python -u' # -u 表示使用无缓冲的二进制终端输出流
project_name = 'iast'
proc_name = 'gunicorn_%s' % project_name # 进程名字
# os.environ.setdefault('DJANGO_SETTINGS_MODULE')

