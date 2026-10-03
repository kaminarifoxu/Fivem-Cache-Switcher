import tempfile
from pathlib import Path
import unittest
import app_theme
class ThemeTests(unittest.TestCase):
 def tearDown(self): app_theme.THEME='light'
 def test_preference_survives_restart(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'theme.json';app_theme.save('dark',path);app_theme.THEME='light';app_theme.load(path)
   self.assertEqual(app_theme.THEME,'dark');self.assertEqual(app_theme.color('#f7f0e3'),'#101113')
 def test_missing_and_invalid_use_light(self):
  app_theme.load('/missing/theme.json');self.assertEqual(app_theme.THEME,'light')
  with self.assertRaises(ValueError):app_theme.save('other','/unused')
 def test_brand_red_is_preserved(self):
  app_theme.THEME='dark';self.assertEqual(app_theme.color('#b82736'),'#b82736')
