#!/usr/bin/env python
# -*- coding=utf8 -*-

import threading
import Queue
import getpass
import re
import time
from math import floor
from random import random
from weibo_login import login as loginToWeibo, S
from bs4 import BeautifulSoup as BS

__DEBUG__ = True

def debug(message):
	global __DEBUG__
	if __DEBUG__:
		print message

def csvGenerator(fd):
	data = ''
	while True:
		buff = fd.read(1024)
		if not buff:
			break
		data += buff
		if not ',' in buff:
			continue
		l = data.split(',')
		count = len(l)
		for i in xrange(count-1):
			yield l[i]
		data = l[count-1]
	yield data

class GetUidThread(threading.Thread):

	uidsVisited = set()

	def __init__(self, uidsQueued, fileLock, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self.uidsQueued = uidsQueued
		self.uidsVisited = self.__class__.uidsVisited

	def get_follow_list(self, uid, i):

		url = 'http://weibo.com/' + str(uid) + '/follow?page=' + str(i)

		html = S.get(url).text

		pattern = r'html":"(<div class="WB_cardwrap S_bg2">[^}]*?)"\}'
		html = html.replace('\\t', '').replace('\\n', '').replace('\\r', '').replace('\\', '')
		# print html
		html_snippet = re.search(pattern, html).group(1)
		
		soup = BS(html_snippet)

		followList = soup.find_all('li', class_='follow_item')
		info = []
		for item in followList:
			d = {}
			kv = [pair.split('=') for pair in item.attrs['action-data'].split('&')]
			for pair in kv:
				d[pair[0]] = pair[1]
			
			mod_info = item.find('dd', class_='mod_info')

			# filter topics
			is_topic = mod_info.find('div', class_='info_name').find('span')
			if is_topic and is_topic.text == '#':
				continue

			nums = mod_info.find('div', class_='info_connect').find_all('span')
			# print nums
			d['following'] = nums[0].find('em').text
			d['follower'] = nums[1].find('em').text
			d['posts'] = nums[2].find('em').text

			address = mod_info.find('div', class_='info_add')
			if address:
				address = address.find('span').text
			introduction = mod_info.find('div', class_='info_intro')
			if introduction:
				introduction = introduction.find('span').text
			follow_from = mod_info.find('div', class_='info_from')
			if follow_from:
				follow_from = follow_from.find('a').text

			d['address'] = address
			d['introduction'] = introduction
			d['follow_from'] = follow_from

			info.append(d)

			if self._qualified(d) and (d['uid'] not in self.uidsVisited) and (d['uid'] not in self.uidsQueued.queue):
				self.uidsQueued.put(d['uid'])

	def _qualified(self, info):
		# return info['following']
		return True

	def run(self):
		while True:
		# for i in range(1):
			try: 
				uid = self.uidsQueued.get(True)
			except Queue.Empty, e:
				print e, '\ntask done'
				return
			
			if 
			print 'getting following list from uid[', uid, ']'
			for i in range(1, 6):

				self.get_follow_list(uid, i)

			self.uidsVisited.add(uid)

			print threading.current_thread()
			print 'visited uids:', len(self.uidsVisited)
			print 'queued uids:', self.uidsQueued.qsize()

			# when task_done() called, count of unfinished tasks goes down,
			# so you call this every time you consume a very single item!!!

			self.uidsQueued.task_done()
			# print self.taskQueue.queue

class Crawler:
	def __init__(self, numGetUidThread = 5, numGetPostsThread = 20, fileUidsQueued = None, fileUidsVisited = None):
		self.numGetUidThread = numGetUidThread
		self.uidToStart = uidToStart
		self.numGetPostsThread = numGetPostsThread
		self.uidsQueued = Queue.Queue()

		self.fdUidsVisited = open(fileUidsQueued, 'at')
		self.fdUidsQueued = open(fileUidsVisited, 'r+t')
		self.fileLock = threading.Lock()

		for line in self.fdUidsQueued:

	def startGetUid(self, q):
		if isinstance(self.uidToStart, list):
			for item in self.uidToStart:
				self.uidsQueued.put(item)
		else:
			self.uidsQueued.put(self.uidToStart)
		for i in range(0, self.numGetUidThread):
			getUidThread = GetUidThread(uidsQueued = self.uidsQueued, fileLock = self.fileLock)
			getUidThread.daemon = True
			getUidThread.start()
		self.uidsQueued.join()

		q.task_done()
	
	def startGetPosts(self, q):

		q.task_done()

	def start(self):
		q = Queue.Queue()
		q.put(1)
		q.put(1)
		t = threading.Thread(target=self.startGetUid, args=(q, ))
		t.daemon = True
		t.start()
		t = threading.Thread(target=self.startGetPosts, args=(q, ))
		t.daemon = True
		t.start()
		q.join()

if __name__ == '__main__':
	username = '18817583755'
	# password = getpass.getpass()
	password = ''
	cookieFile = 'cookies.txt'
	if loginToWeibo(username = username, pwd = password, cookies_file = cookieFile):
		fileUidsQueued = './data/uidsQueued.txt'
		fileUidsVisited = './data/uidsQueued.txt'
		crawler = Crawler(numGetUidThread = 2, fileUidsQueued = fileUidsQueued, fileUidsVisited = fileUidsVisited)
		crawler.start()
	else:
		raise RuntimeError("Login to weibo failed")