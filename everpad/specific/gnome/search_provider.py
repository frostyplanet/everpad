#!/usr/bin/env python
# coding:utf-8

import dbus
import dbus.service
import dbus.mainloop.glib
import json
from html2text import html2text
import signal
import sys
from everpad.tools import get_provider, get_pad, resource_filename
from everpad.basetypes import Note, Tag, Notebook, Place, Resource
from everpad.specific import AppClass
from PySide.QtCore import Slot, QSettings


def find_match_in_result(content, term, range_before=30, range_after=60):
    preview = html2text(content)
    preview = preview.replace("\r", " ")
    preview = preview.replace("\n", " ")
    pos = preview.find(term)
    if pos >= 0:
        end = min(pos + range_after, len(preview))
        begin = max(pos - range_before, 0)
        preview = preview[begin: end]
    else:
        preview = preview[: range_before + range_after]
    # should eliminate html tags, otherwise will corrupt display
    preview = preview.replace("<", "&lt;")  
    preview = preview.replace(">", "&gt;")
    return preview



class GnomeShellSearchProvider(dbus.service.Object):

    def __init__(self, *args, **kwargs):
        super(GnomeShellSearchProvider, self).__init__(*args, **kwargs)
        self.provider = get_provider()
        self.pad = get_pad()

    def _run_search(self, terms):
        search = " ".join(terms)
        notebooks = dbus.Array([], signature='i')
        tags = dbus.Array([], signature='i')
        place = 0
        result = []
        #TODO search by tag or notebook
        notes = self.provider.find_notes(
               search, notebooks, tags, place,
               1000, Note.ORDER_TITLE, -1,
               )
        for note_struct in notes:
            note = Note.from_tuple(note_struct)
            result.append(json.dumps({'id': note.id, 
                    'title': note.title,
                    'content': note.content, # html
                    'terms': search,
                    }))
        return result


    @dbus.service.method("org.gnome.Shell.SearchProvider2",
            in_signature='as', out_signature='as')
    def GetInitialResultSet(self, terms):
        result = self._run_search(terms)
        return dbus.Array(result, signature='s')

    @dbus.service.method("org.gnome.Shell.SearchProvider2",
            in_signature='asas', out_signature='as')
    def GetSubsearchResultSet(self, previous_results, terms):
        result = self._run_search(terms)
        return dbus.Array(result, signature='s')

    
    @dbus.service.method("org.gnome.Shell.SearchProvider2",
            in_signature="as", out_signature="aa{sv}")
    def GetResultMetas(self, identifiers):
        result = []
        for n_s in identifiers:
            data = json.loads(n_s)
            result.append(dbus.Dictionary({'id': n_s, 
                'name': data['title'],
                'description': find_match_in_result(data['content'], data['terms'])
                }))
        return dbus.Array(result, "a{sv}")

    @dbus.service.method("org.gnome.Shell.SearchProvider2",
            in_signature='sasu')
    def ActivateResult(self, identifier, terms, timestamp):
        data = json.loads(identifier)
        pad = get_pad()
        pad.open_with_search_term(data['id'], " ".join(terms))



    @dbus.service.method("org.gnome.Shell.SearchProvider2",
            in_signature='asu', out_signature='')
    def LaunchSearch(self, terms, timestamp):
        return



class GnomeShellSearchProviderDaemon(AppClass):

    def __init__(self, *args, **kwargs):
        AppClass.__init__(self, *args, **kwargs)
        session_bus = dbus.SessionBus()
        self.bus = dbus.service.BusName("com.everpad.gnome.SearchProvider", session_bus)
        self.service = GnomeShellSearchProvider(session_bus, "/com/everpad/gnome/SearchProvider")
 

    @Slot()
    def terminate(self):
        self.quit()


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    app = GnomeShellSearchProviderDaemon(sys.argv)
    app.exec_()

if __name__ == '__main__':
    main()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
