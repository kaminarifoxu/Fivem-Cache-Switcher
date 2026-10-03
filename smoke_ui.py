# Copyright (c) 2026 GANOMABI / amiinarii.
"""Exercise the real Tk UI in both languages without opening FiveM or making network requests."""
import os
from pathlib import Path
import tempfile
import customtkinter as ctk
import cache_switcher

errors=[]
original=ctk.CTk.mainloop

def automated_loop(self):
    self.check_updates=lambda *a,**k:None
    self.load_adapters=lambda:None
    self.periodic_servers=lambda:None
    self.report_callback_exception=lambda *args: errors.append(args)
    def verify():
        try:
            assert self.nav['servers'].cget('text')=='Daftar server'
            self.show_page('servers')
            self.change_language('English')
            assert self.nav['servers'].cget('text')=='Server list'
            assert self.page=='servers'
            assert len(self.catalog['servers'])>=5
            self.change_language('Indonesia')
            assert self.nav['servers'].cget('text')=='Daftar server'
            self.show_page('tools')
            self.update_idletasks()
        except Exception as exc: errors.append(exc)
        finally: self.after(500,self.close)
    self.after(1800,verify)
    self.after(10000,self.close)
    original(self)

with tempfile.TemporaryDirectory() as tmp:
    os.environ['LOCALAPPDATA']=tmp
    ctk.CTk.mainloop=automated_loop
    try: cache_switcher.main()
    finally: ctk.CTk.mainloop=original
if errors: raise AssertionError(errors)
print('PASS: language switching, catalog UI, and page navigation.')
