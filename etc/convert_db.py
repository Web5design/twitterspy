#!/usr/bin/env python

import sys
sys.path.extend(["lib", "../lib"])

from sqlite3 import dbapi2 as sqlite

from twisted.internet import reactor, defer

from twitterspy import db

GET_USERS="""
select jid, username, password, active, status, min_id, language,
       auto_post, friend_timeline_id, direct_message_id, created_at, id
    from users
"""

GET_TRACKS="""
select query
    from tracks join user_tracks on (tracks.id = user_tracks.track_id)
    where user_tracks.user_id = ?
"""

DB=sqlite.connect(sys.argv[1])

CUR=DB.cursor()

def parse_timestamp(ts):
    return None

@defer.deferredGenerator
def create_database():
    couch = db.get_couch()
    d = couch.createDB(db.DB_NAME)
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    doc="""
{"language":"javascript","views":{"counts":{"map":"function(doc) {\n  if(doc.doctype == 'User') {\n    emit(null, {users: 1, tracks: doc.tracks.length});\n  }\n}","reduce":"function(key, values) {\n  var result = {users: 0, tracks: 0};\n  values.forEach(function(p) {\n     result.users += p.users;\n     result.tracks += p.tracks;\n  });\n  return result;\n}"}}}
"""
    d = couch.saveDoc(db.DB_NAME, doc, '_design/counts')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    doc="""
{"language":"javascript","views":{"query_counts":{"map":"function(doc) {\n  if(doc.doctype == 'User') {\n    doc.tracks.forEach(function(query) {\n      emit(query, 1);\n    });\n  }\n}","reduce":"function(key, values) {\n   return sum(values);\n}"}}}
"""

    d = couch.saveDoc(db.DB_NAME, doc, '_design/query_counts')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    doc="""
{"language":"javascript","views":{"active":{"map":"function(doc) {\n  if(doc.doctype == 'User' && doc.active) {\n    emit(null, doc._id);\n  }\n}"}}}
"""

    d = couch.saveDoc(db.DB_NAME, doc, '_design/users')
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()

    reactor.callLater(0, load_records)

@defer.deferredGenerator
def load_records():
    for r in CUR.execute(GET_USERS).fetchall():
        user = db.User()
        user.jid = r[0]
        user.username = r[1]
        user.password = r[2]
        user.active = bool(r[3])
        user.status = r[4]
        user.min_id = r[5]
        user.language = r[6]
        user.auto_post = bool(r[7])
        user.friend_timeline_id = r[8]
        user.direct_message_id = r[9]
        user.created_at = parse_timestamp(r[10])

        for tr in CUR.execute(GET_TRACKS, [r[11]]).fetchall():
            user.track(tr[0])

        d = user.save()
        wfd = defer.waitForDeferred(d)
        yield wfd
        print "Did %s: %s" % (r[0], wfd.getResult())

    reactor.stop()

reactor.callWhenRunning(create_database)
reactor.run()
