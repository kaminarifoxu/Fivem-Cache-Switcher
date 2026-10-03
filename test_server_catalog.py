import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import server_catalog as catalog
import i18n

class ServerCatalogTests(unittest.TestCase):
    def data(self):
        return {'schema_version':1,'servers':[{'id':'test','name':'Test City','join_code':'abc123','description':{'id':'Halo','en':'Hello'}}]}
    def test_bundled_catalog_is_valid(self):
        self.assertGreaterEqual(len(catalog.read_catalog(Path(__file__).with_name('servers.json'))['servers']), 5)
    def test_sync_and_invalid_remote_keep_cached_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'cache.json'
            with patch.object(catalog,'urlopen',return_value=io.BytesIO(json.dumps(self.data()).encode())):
                catalog.sync_catalog(path)
            original = path.read_bytes()
            with patch.object(catalog,'urlopen',return_value=io.BytesIO(b'{broken')):
                with self.assertRaises(ValueError): catalog.sync_catalog(path)
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(catalog.load_catalog(path,'missing'),self.data())
    def test_join_target_rejects_commands_and_other_schemes(self):
        for code in ('abc123;quit','https://example.com','abc123?x=1','../abc123',''):
            with self.assertRaises(ValueError): catalog.connect_uri(code)
        self.assertEqual(catalog.connect_uri('abc123'),'fivem://connect/cfx.re/join/abc123')
    def test_duplicate_ids_rejected(self):
        data=self.data();data['servers'].append(copy.deepcopy(data['servers'][0]))
        with self.assertRaises(ValueError): catalog.validate_catalog(data)
    def test_language_preference_survives_restart(self):
        old=i18n.LANGUAGE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'ui.json'
                i18n.set_language('en',path)
                self.assertEqual(i18n.tr('Cek update'),'Check for updates')
                i18n.LANGUAGE='id';i18n.load(path)
                self.assertEqual(i18n.LANGUAGE,'en')
                i18n.set_language('id',path)
                self.assertEqual(i18n.tr('Cek update'),'Cek update')
        finally:i18n.LANGUAGE=old
