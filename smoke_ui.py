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
    self.periodic_status=lambda:None
    self.report_callback_exception=lambda *args: errors.append(args)
    def verify():
        try:
            assert self.nav['servers'].cget('text')=='Daftar server'
            assert self.language_selector.master.master is self.pages['tools']
            assert self.exe_label.master.master is self.pages['tools']
            assert self.update_status.master.master is self.pages['tools']
            def labels(widget):
                result = []
                for child in widget.winfo_children():
                    try: result.append(child.cget('text'))
                    except Exception: pass
                    result.extend(labels(child))
                return result
            assert 'Pilih FiveM.exe' not in labels(self.sidebar)
            assert 'Cek update' not in labels(self.sidebar)
            assert 'List server' in labels(self.pages['servers'])
            self.show_page('servers')
            self.latest_release = {'version':'99.0.0'}
            self.set_update_status('Update tersedia: v99.0.0')
            self.update_idletasks()
            assert self.update_banner.winfo_viewable()
            self.show_update_notice(release=self.latest_release)
            self.update()
            assert self.update_dialog.winfo_viewable()
            assert not self.update_dialog.overrideredirect()
            self.update_dialog.grab_release()
            self.update_dialog.destroy()
            self.update_dialog=None
            self.change_language('English')
            assert self.nav['servers'].cget('text')=='Server list'
            assert self.page=='servers'
            self.update_idletasks()
            assert self.update_banner.winfo_viewable()
            self.results.append(('update_progress', .5))
            self.poll()
            self.update_idletasks()
            assert self.global_update_progress.winfo_viewable()
            assert self.global_update_progress.get()==.5
            assert len(self.catalog['servers'])>=5
            self.server_statuses = {self.catalog['servers'][0]['join_code']: {'available':True,'clients':123,'maximum':2048,'description':'Official description','checked':'12:00:00'}}
            self.render_servers()
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
