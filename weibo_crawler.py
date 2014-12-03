#!/usr/bin/env python
# -*- coding=utf8 -*-

import threading
import Queue
import getpass
import re
import time
import signal
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

	def __init__(self, uidsToVisit, uidsVisited, fileLock, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self.uidsToVisit = uidsToVisit
		self.uidsVisited = uidsVisited
		self.__terminated__ = False
		self.__fileLock__ = fileLock

	def get_follow_list(self, uid, i):

		url = 'http://weibo.com/' + str(uid) + '/follow?page=' + str(i)

		html = S.get(url).text

		pattern = r'html":"(<div class="WB_cardwrap S_bg2">[^}]*?)"\}'
		html = html.replace('\\t', '').replace('\\n', '').replace('\\r', '').replace('\\', '')
		# print html
		try:
			html_snippet = re.search(pattern, html).group(1)
		except Exception, e:
			print e
			return
		
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

			if self._qualified(d) and (d['uid'] not in self.uidsVisited) and (d['uid'] not in self.uidsToVisit):
				self.uidsToVisit.put(d['uid'])

	def _qualified(self, info):
		# return info['following']
		return True

	def run(self):
		while not self.__terminated__:
		# for i in range(1):
			try: 
				uid = self.uidsToVisit.get(True)
			except Queue.Empty, e:
				print e, '\ntask done'
				return
			
			print 'getting following list from uid[', uid, ']'

			for i in range(1, 6):
				self.get_follow_list(uid, i)

			self.uidsVisited.add(uid)

			print threading.current_thread()
			print 'visited uids:', len(self.uidsVisited)
			print 'queued uids:', len(self.uidsToVisit)

			# when task_done() called, count of unfinished tasks goes down,
			# so you call this every time you consume a very single item!!!

			# self.uidsToVisit.task_done()
			# print self.taskQueue.queue
		# self.__fileLock__.acquire()
		# self.__fileLock__.release()

class GetPostsThread(threading.Thread):
	def __init__(self, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)


class Crawler:
	def __init__(self, numGetUidThread = 5, numGetPostsThread = 20, fileuidsToVisit = None, fileUidsVisited = None):
		self.numGetUidThread = numGetUidThread
		self.numGetPostsThread = numGetPostsThread
		self.uidsToVisit = set()
		self.uidsVisited = set()
		self.threads = []

		self.fduidsToVisit = open(fileuidsToVisit, 'r+t')
		self.fdUidsVisited = open(fileUidsVisited, 'r+t')
		self.fileLock = threading.Lock()

	def startGetUid(self, q):
		iterQueued = csvGenerator(self.fduidsToVisit)
		for uid in iterQueued:
			if uid != '':
				self.uidsToVisit.put(uid)
		iterVisited = csvGenerator(self.fdUidsVisited)
		for uid in iterVisited:
			if uid != '':
				self.uidsVisited.add(uid)
			print self.uidsVisited
		# self.fduidsToVisit.truncate()

		for i in range(0, self.numGetUidThread):
			getUidThread = GetUidThread(uidsToVisit = self.uidsToVisit, uidsVisited = self.uidsVisited, fileLock = self.fileLock)
			self.threads.append(getUidThread)
			getUidThread.daemon = True
			getUidThread.start()
		self.uidsToVisit.join()

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
		# q.join()

	def stop(self):
		for thread in self.threads:
			thread.__terminated__ = True

		# wait until all thread finish current run
		for thread in self.threads:
			thread.join()

		# write uids queued into uidsToVisit.txt
		self.fduidsToVisit.truncate()
		self.fduidsToVisit.seek(0)
		for uid in list(self.uidsToVisit)[:-1]:
			self.fduidsToVisit.write(uid)
			self.fduidsToVisit.write(',')
		self.fduidsToVisit.write(self.uidsToVisit[-1])
		self.fduidsToVisit.close()

		# write uids visited into uidsVisited.txt
		self.fdUidsVisited.truncate()
		self.fdUidsVisited.seek(0)
		for uid in list(self.uidsVisited)[:-1]:
			self.fdUidsVisited.write(uid)
			self.fdUidsVisited.write(',')
		self.fdUidsVisited.write(list(self.uidsVisited)[-1])
		self.fdUidsVisited.close()
		# print self.uidsToVisit.queue

def exitHandler(*args, **kwargs):
	# print 'Exit'
	# with open('exit.txt', 'a+t') as fd:
	# 	fd.write('exit!\n')
	global crawler
	crawler.stop()
	exit()

if __name__ == '__main__':
	username = '18817583755'
	# password = getpass.getpass()
	password = ''
	cookieFile = 'cookies.txt'
	if loginToWeibo(username = username, pwd = password, cookies_file = cookieFile):
		fileuidsToVisit = './data/uidsToVisit.txt'
		fileUidsVisited = './data/uidsVisited.txt'
		crawler = Crawler(numGetUidThread = 2, fileuidsToVisit = fileuidsToVisit, fileUidsVisited = fileUidsVisited)
		crawler.start()
 
		signal.signal(signal.SIGINT, exitHandler)

		while True:
			pass
	else:
		raise RuntimeError("Login to weibo failed")