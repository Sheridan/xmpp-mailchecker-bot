#!/usr/bin/env python2
# -*- coding: utf8 -*-

import os, sys, string, sqlite3

class CDBStorage(object):

    def init(self, db_file):
	db_exists = os.path.exists(db_file)
	self.db = sqlite3.connect(db_file, check_same_thread = False)
	if not db_exists:
	    self.db.cursor().execute('CREATE TABLE records (jid VARCHAR(256), postbox VARCHAR(256), server VARCHAR(256), login VARCHAR(256), password VARCHAR(256))')
	    self.db.cursor().execute('CREATE TABLE messages (jid VARCHAR(256), postbox VARCHAR(256), message_hash VARCHAR(64))')
	    self.db.cursor().execute('create index records_index_jid on records (jid)')
	    self.db.cursor().execute('create index records_index on records (jid, postbox)')
	    self.db.cursor().execute('create index messages_index_jid on messages (jid)')
	    self.db.cursor().execute('create index messages_index on messages (jid, postbox)')
	    self.db.commit()
	
    def getRecord(self, jid, postbox):
	q = self.db.cursor()
	q.execute('select server, login, password from records where jid=? and postbox=?', (jid, postbox))
	for row in q:
	    return {'jid': jid, 'postbox': postbox, 'server': row[0], 'login': row[1], 'password': row[2]}
	    
    def getRecords(self, jid):
	q = self.db.cursor()
	q.execute('select postbox, server, login, password from records where jid=?', [jid])
	result=list()
	for row in q:
	    result.append({'jid': jid, 'postbox': row[0], 'server': row[1], 'login': row[2], 'password': row[3]})
	return result

    def getJids(self):
	q = self.db.cursor()
	q.execute('select distinct jid from records')
	result=list()
	for row in q:
	    result.append(row[0])
	return result

    def storeRecord(self, jid, postbox, server, login, password):
	self.db.cursor().execute('INSERT INTO records VALUES (?, ?, ?, ?, ?)', (jid, postbox, server, login, password))
	self.db.commit()
	
    def editRecord(self, jid, postbox, server, login, password):
	self.db.cursor().execute('update records set server=?, login=?, password=? wherejid=? and postbox=?)', (server, login, password, jid, postbox))
	self.db.commit()
	
    def removeRecord(self, jid, postbox):
	self.db.cursor().execute('delete from records where jid=? and postbox=?', (jid, postbox))
	self.db.commit()
	self.resetMessageHashes(jid, postbox)
	
    def checkMessageHashExists(self, jid, postbox, message_hash):
	q = self.db.cursor()
	q.execute('select count(*) from messages where jid=? and postbox=? and message_hash=?', (jid, postbox, message_hash))
	result = False
	for row in q:
	    if int(row[0]) > 0:
		result = True
	    else:
		self.db.cursor().execute('INSERT INTO messages VALUES (?, ?, ?)', (jid, postbox, message_hash))
		self.db.commit()
	    break
	return result

    def cleanMessageHashes(self, jid, postbox, hashes):
	q = self.db.cursor()
	q.execute('select message_hash from messages where jid=? and postbox=?', (jid, postbox))
	for row in q:
	    if row[0] not in hashes:
		self.db.cursor().execute('delete from messages where jid=? and postbox=? and message_hash=?', (jid, postbox, row[0]))
		self.db.commit()
	
    def resetMessageHashes(self, jid, postbox):
	if postbox != '':
	    self.db.cursor().execute('delete from messages where jid=? and postbox=?', (jid, postbox))
	else:
	    self.db.cursor().execute('delete from messages where jid=?', [jid])
	self.db.commit()

