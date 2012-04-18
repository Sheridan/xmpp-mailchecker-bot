#!/usr/bin/env python2
# -*- coding: utf8 -*-

import sys, string, poplib, imaplib, time, hashlib, traceback, re
from email import parser
from email.header import decode_header
from threading import Thread, Lock

################################################  exception ####################################################################
class ECheckError(Exception):
    def __init__(self, value):
	self.value = value
    def __str__(self):
	return repr(self.value)
################################################  exception ####################################################################
################################################  mail checker ####################################################################
class CMailChecker(Thread):
    def __init__(self, bot, i18, config, storage, logger, jid, postbox, interval):
	Thread.__init__(self)
	self.logger = logger
	self.config = config
	self.storage = storage
	self.i18 = i18
	self.bot = bot
	self.jid = jid
	self.postbox = postbox
	self.interval = interval
	self.terminate = False
	self.check_now = False
	self.imap_box_filter = re.compile('(%s)'%'|'.join(self.config['imap']['skip_folders']))
	self.status = self.i18['mailchecker_status']['sleep']
	self.used_protocol = 'unknown'

    def decodeText(self, header_text):
	headers = decode_header(header_text)
	formatted = u''
	for text, charset in headers:
	    if text:
		text_part = unicode(text, charset or "utf-8")
		for m in re.findall(r'(=\?.+?\?=)', text_part):
		    hpart = decode_header(m)
		    text_part = text_part.replace(m, unicode(hpart[0][0], hpart[0][1] or "utf-8"))
		formatted += text_part
	for repl_from, repl_to in self.config['headers_text_replaces']:
	    formatted = re.sub(repl_from, repl_to, formatted, 0)
	return formatted

    def checkPop(self, record):
	result = ''
	messages_count = 0
	self.logger.log(self.i18['log']['try_check_mail']%('POP3', record['server'], self.jid))
	connection = None
	self.status = self.i18['mailchecker_status']['connect']%('POP3', record['server'])
	if self.used_protocol == 'unknown' or self.used_protocol == 'POP3.SSL':
	    try:
		connection = poplib.POP3_SSL(record['server'])
		self.used_protocol = 'POP3.SSL'
	    except:
		self.logger.log(self.i18['log']['proto_ssl_err']%('POP3', traceback.format_exc()))
		self.used_protocol = 'unknown'
	if self.used_protocol == 'unknown' or self.used_protocol == 'POP3':
	    try:
		connection = poplib.POP3(record['server'])
		self.used_protocol = 'POP3'
	    except:
		self.logger.log(self.i18['log']['proto_err']%('POP3.SSL', traceback.format_exc()))
		self.used_protocol = 'unknown'
		raise ECheckError(self.i18['log']['proto_conn_failed']%('POP3', record['server'], traceback.format_exc()))
	self.status = self.i18['mailchecker_status']['check']%(self.used_protocol, record['server'])
	connection.user(record['login'])
	connection.pass_(record['password'])
	
	messages = [connection.retr(i) for i in range(connection.stat()[0], 0, -1)]
	messages = ["\n".join(mssg[1]) for mssg in messages]
	messages = [parser.Parser().parsestr(mssg, True) for mssg in messages]

	hashes = list()
	for message in messages:
	    message_hash = self.buildMessageHash(message)
	    hashes.append(message_hash)
	    if not self.storage.checkMessageHashExists(self.jid, record['postbox'], message_hash):
		result += self.i18['user_messages']['new_post_mail']%(self.decodeText(message['From']),self.decodeText(message['Subject']))
		messages_count += 1
	
	self.status = self.i18['mailchecker_status']['disconnect']%(self.used_protocol, record['server'])
	connection.quit()
	self.status = self.i18['mailchecker_status']['cache_clean']%(record['postbox'])
	self.storage.cleanMessageHashes(self.jid, record['postbox'], hashes)
	
	self.logger.log(self.i18['log']['check_done']%(self.used_protocol, record['server'], self.jid))
	self.status = self.i18['mailchecker_status']['sleep']
	return {"result": result, "msg_count": messages_count}
	
    def checkImap(self, record):
	result = ''
	messages_count = 0
	self.logger.log(self.i18['log']['try_check_mail']%('IMAP4', record['server'], self.jid))
	connection = None
	self.status = self.i18['mailchecker_status']['connect']%('IMAP4', record['server'])
	if self.used_protocol == 'unknown' or self.used_protocol == 'IMAP4.SSL':
	    try:
		connection = imaplib.IMAP4_SSL(record['server'])
		self.used_protocol = 'IMAP4.SSL'
	    except:
		self.logger.log(self.i18['log']['proto_ssl_err']%('IMAP4', traceback.format_exc()))
		self.used_protocol = 'unknown'
	if self.used_protocol == 'unknown' or self.used_protocol == 'IMAP4':
	    try:
		connection = imaplib.IMAP4(record['server'])
		self.used_protocol = 'IMAP4'
	    except:
		self.logger.log(self.i18['log']['proto_err']%('IMAP4.SSL', traceback.format_exc()))
		self.used_protocol = 'unknown'
		raise ECheckError(self.i18['log']['proto_conn_failed']%('IMAP4', record['server'], traceback.format_exc()))
	self.status = self.i18['mailchecker_status']['check']%(self.used_protocol, record['server'])
	connection.login(record['login'], record['password'])
	
	hashes = list()
	
	for directory in connection.list()[1]:
	    matches = re.finditer(r'"(.+?)"', directory)
	    results = [match.group(1) for match in matches]
	    directory = results[1]
	    
	    if not self.imap_box_filter.match(directory): 
		connection.select(directory, True)
		typ, data = connection.search(None, 'UNSEEN')
		if data[0] != '':
		    messages = [connection.fetch(i, '(BODY[HEADER.FIELDS (SUBJECT FROM)])')[1][0][1] for i in data[0].split(' ')]
		    messages = [parser.Parser().parsestr(mssg, True) for mssg in messages]

		    for message in messages:
			if message['From']:
			    message_hash = self.buildMessageHash(message)
			    hashes.append(message_hash)
			    if not self.storage.checkMessageHashExists(self.jid, record['postbox'], message_hash):
				result += self.i18['user_messages']['new_post_mail']%(self.decodeText(message['From']),self.decodeText(message['Subject']))
				messages_count += 1

	self.status = self.i18['mailchecker_status']['cache_clean']%(record['postbox'])
	self.storage.cleanMessageHashes(self.jid, record['postbox'], hashes)
	self.status = self.i18['mailchecker_status']['disconnect']%(self.used_protocol, record['server'])
	connection.close()
	connection.logout()
	self.logger.log(self.i18['log']['check_done']%(self.used_protocol, record['server'], self.jid))
	self.status = self.i18['mailchecker_status']['sleep']
	return {"result": result, "msg_count": messages_count}
	
    def buildMessageHash(self, message):
	text = ''
	for header in ('From', 'Subject', 'Message-Id', 'Date', 'Received', 'Return-Path', 'X-Mailer'):
	    if message[header]:
		text += message[header]
	return hashlib.sha224(text).hexdigest()
	
    def checkMail(self):
	result = ''
	record = self.storage.getRecord(self.jid, self.postbox)
	if self.used_protocol == 'unknown' or self.used_protocol == 'IMAP4' or self.used_protocol == 'IMAP4.SSL':
	    try:
		boxResult = self.checkImap(record)
		if int(boxResult['msg_count']) > 0:
		    result += self.i18['user_messages']['new_post']%(record['postbox'], boxResult['result'], boxResult['msg_count'])
	    except ECheckError as e_imap:
		result += "%s\n%s"%(e_imap.value, e_pop.value)
	if self.used_protocol == 'unknown' or self.used_protocol == 'POP3' or self.used_protocol == 'POP3.SSL':
	    try:
	        boxResult = self.checkPop(record)
	        if int(boxResult['msg_count']) > 0:
		    result += self.i18['user_messages']['new_post']%(record['postbox'], boxResult['result'], boxResult['msg_count'])
	    except ECheckError as e_pop:
		result += "%s\n%s"%(e_imap.value, e_pop.value)
	return result

    def GoOn(self):
	while not self.terminate:
	    result = self.checkMail()
	    if result != '':
		self.bot.sendMessage(self.jid, result)
	    for x in range(0, self.interval):
		time.sleep(1)
		if self.terminate or self.check_now:
		    self.check_now = False
		    break

    def run(self):
	self.logger.log(self.i18['log']['mailchecker_thread_started']%self.jid)
	self.GoOn()

    def checkNow(self):
	self.check_now = True
	
    def stop(self):
	self.terminate = True
################################################  mail checker ####################################################################
################################################  mail checkers ####################################################################
class CMailCheckers(object):
    def __init__(self, bot, i18, config, storage, logger):
	self.logger = logger
	self.config = config
	self.storage = storage
	self.i18 = i18
	self.bot = bot
	self.checkers = []
	
    def add(self, jid, postbox):
	checker = None
	for ch in self.checkers:
	    if ch['jid'] == jid and ch['postbox'] == postbox:
		checker = ch['ch']
		break
	if not checker:
	    checker = CMailChecker(self.bot, self.i18, self.config, self.storage, self.logger, jid, postbox, int(self.config['mail_check_interval']))
	    self.checkers.append({ 'jid': jid, 'postbox': postbox, 'ch': checker })
	    checker.start()
	
    def checkNow(self, jid):
	for checker in self.checkers:
	    if checker['jid'] == jid:
		checker['ch'].checkNow()

    def statuses(self):
	st = '\n'
	for checker in self.checkers:
	    st += '%s, %s: %s\n'%(checker['jid'], checker['postbox'], checker['ch'].status)
	return st

    def stop(self):
	for checker in self.checkers:
	    checker['ch'].stop()
	    checker['ch'].join()
################################################  mail checkers ####################################################################

