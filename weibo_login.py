#!/usr/bin/env python
#coding=utf8

'''
Created on Mar 18, 2013

@author: yoyzhou
'''

'''
Updated on APril 16, 2014

@author: wanghaisheng
'''

"""
Nov. 19, 2014
change to advanced APIs such as requests, beautifulsoup4, etc.
dragonly<liyilongko@gmail.com>
"""

try:
	import os
	import sys
	import urllib
	import base64
	import re
	import hashlib
	import json
	import rsa
	import binascii
	import getpass
	import requests
	import pickle
	from bs4 import BeautifulSoup as BS

except ImportError:
		print >> sys.stderr, """\

There was a problem importing one of the Python modules required.
The error leading to this problem was:

%s

Please install a package which provides this module, or
verify that the module is installed correctly.

It's possible that the above module doesn't match the current version of Python,
which is:

%s

""" % (sys.exc_info(), sys.version)
		sys.exit(1)

reload(sys)
sys.setdefaultencoding('utf-8')

S = requests.Session()

def get_prelogin_status(username):
	"""
	Perform prelogin action, get prelogin status, including servertime, nonce, rsakv, etc.
	"""
	prelogin_url = 'http://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.preloginCallBack&su=' + get_user(username) + '&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.18)';
	data = S.get(prelogin_url).text
	p = re.compile('\((.*)\)')
	
	try:
		json_data = p.search(data).group(1)
		data = json.loads(json_data)
		servertime = str(data['servertime'])
		nonce = data['nonce']
		rsakv = data['rsakv']
		return servertime, nonce, rsakv
	except:
		print 'Getting prelogin status error!'
		return None


def login(username, pwd, cookies_file):
	""""
		Login with use name, password and cookies.
		(1) If cookie file exists then try to load cookies;
		(2) If no cookies found then do login
	"""
	global S
	if os.path.exists(cookies_file):
		try:
			with open(cookies_file, 'rt') as fd:
				cookies_dict = requests.utils.cookiejar_from_dict(pickle.load(fd))
				# print 'cookies from file:\n', cookies_dict
				# S = requests.Session(cookies=cookies_dict)
				S.cookies = cookies_dict
		except Exception, e:
			print 'Loading cookies error'
			print e
			return do_login(username, pwd, cookies_file)

		print 'Loading cookies success'
		return 1
	else:   #If no cookies found
		return do_login(username, pwd, cookies_file)


def do_login(username,pwd,cookies_file):
	""""
	Perform login action with use name, password and saving cookies.
	@param username: login user name
	@param pwd: login password
	@param cookies_file: file name where to save cookies when login succeeded 
	"""
	global S
	login_data = {
		'entry': 'weibo',
		'gateway': '1',
		'from': '',
		'savestate': '7',
		'userticket': '1',
		'pagerefer':'',
		'vsnf': '1',
		'su': '',
		'service': 'miniblog',
		'servertime': '',
		'nonce': '',
		'pwencode': 'rsa2',
		'rsakv': '',
		'sp': '',
		'encoding': 'UTF-8',
		'prelt': '45', 
		'url': 'http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack',
		'returntype': 'META'
		}

	login_url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18)'
	try:
		servertime, nonce, rsakv = get_prelogin_status(username)
	except:
		return 0
	
	login_data['servertime'] = servertime
	login_data['nonce'] = nonce
	login_data['su'] = get_user(username)
	login_data['sp'] = get_pwd_rsa(pwd, servertime, nonce)
	login_data['rsakv'] = rsakv
	# login_data = urllib.urlencode(login_data)
	http_headers = {'User-Agent':'Mozilla/5.0 (X11; Linux i686; rv:8.0) Gecko/20100101 Firefox/8.0'}

	text = requests.get(login_url, params=login_data, headers=http_headers).text
	# print text
	p = re.compile(r"location\.replace\('(.*?)'\)")
	try:
		#Search login redirection URL
		login_url = p.search(text).group(1)
		data = s.get(login_url).text

		patt_feedback = 'feedBackUrlCallBack\((.*)\)'
		p = re.compile(patt_feedback, re.MULTILINE)
		
		feedback = p.search(data).group(1)
		feedback_json = json.loads(feedback)
		if feedback_json['result']:
			cookies_dict = requests.utils.dict_from_cookiejar(s.cookies)
			print cookies_dict
			with open('cookies.txt', 'wt') as fd:
				pickle.dump(cookies_dict, fd)
			return 1
		else:
			return 0
	except:
		return 0


def get_pwd_wsse(pwd, servertime, nonce):
	"""
		Get wsse encrypted password
	"""
	pwd1 = hashlib.sha1(pwd).hexdigest()
	pwd2 = hashlib.sha1(pwd1).hexdigest()
	pwd3_ = pwd2 + servertime + nonce
	pwd3 = hashlib.sha1(pwd3_).hexdigest()
	return pwd3

def get_pwd_rsa(pwd, servertime, nonce):
	"""
		Get rsa2 encrypted password, using RSA module from https://pypi.python.org/pypi/rsa/3.1.1, documents can be accessed at 
		http://stuvel.eu/files/python-rsa-doc/index.html
	"""
	#n, n parameter of RSA public key, which is published by WEIBO.COM
	#hardcoded here but you can also find it from values return from prelogin status above
	weibo_rsa_n = 'EB2A38568661887FA180BDDB5CABD5F21C7BFD59C090CB2D245A87AC253062882729293E5506350508E7F9AA3BB77F4333231490F915F6D63C55FE2F08A49B353F444AD3993CACC02DB784ABBB8E42A9B1BBFFFB38BE18D78E87A0E41B9B8F73A928EE0CCEE1F6739884B9777E4FE9E88A1BBE495927AC4A799B3181D6442443'
	
	#e, exponent parameter of RSA public key, WEIBO uses 0x10001, which is 65537 in Decimal
	weibo_rsa_e = 65537
	message = str(servertime) + '\t' + str(nonce) + '\n' + str(pwd)
	
	#construct WEIBO RSA Publickey using n and e above, note that n is a hex string
	key = rsa.PublicKey(int(weibo_rsa_n, 16), weibo_rsa_e)
	
	#get encrypted password
	encropy_pwd = rsa.encrypt(message, key)
	#trun back encrypted password binaries to hex string
	return binascii.b2a_hex(encropy_pwd)


def get_user(username):
	username_ = urllib.quote(username)
	username = base64.encodestring(username_)[:-1]
	return username


if __name__ == '__main__':
	
	
	username = '18817583755'
	# pwd = getpass.getpass()
	pwd = ''
	cookies_file = 'cookies.txt'
	
	if login(username, pwd, cookies_file):
		print 'Login WEIBO succeeded'
		# html = S.get('http://weibo.com/p/1035051708942053/follow?page=5').text
		html = S.get('http://weibo.com/p/1035051708942053/follow?page=5').text

		pattern = r'html":"(<div class="WB_cardwrap S_bg2">[^}]*?)"\}'
		html = html.replace('\\t', '').replace('\\n', '').replace('\\r', '').replace('\\', '')
		# print html
		html_snippet = re.search(pattern, html).group(1)
		
		soup = BS(html_snippet)
		# print soup.prettify()

		with open('html', 'w') as fd:
			# fd.write(html)
			# fd.write('='*80)
			fd.write(soup.prettify())

		followList = soup.find_all('li', class_='follow_item')
		info = []
		for item in followList:
			d = {}
			kv = [pair.split('=') for pair in item.attrs['action-data'].split('&')]
			for pair in kv:
				d[pair[0]] = pair[1]
			
			mod_info = item.find('dd', class_='mod_info')

			nums = mod_info.find('div', class_='info_connect').find_all('span')
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

		for i in info:
			for key in i.keys():
				print key, ':', i[key]
			print '-'*10

	else:
		print 'Login WEIBO failed'