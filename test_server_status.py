import unittest
from unittest.mock import patch
from server_status import parse_status, fetch_statuses, page_url

class ServerStatusTests(unittest.TestCase):
    def test_counts_and_official_description(self):
        data=parse_status({'Data':{'clients':0,'svMaxclients':2048,'vars':{'sv_projectDesc':'^1Dream Big Live Twice'}}})
        self.assertEqual(data['clients'],0)
        self.assertEqual(data['description'],'Dream Big Live Twice')
        self.assertTrue(data['available'])
    def test_invalid_counts_are_not_displayed(self):
        for count in (-1,True,'10'):
            with self.assertRaises(ValueError):parse_status({'Data':{'clients':count,'svMaxclients':100}})
    def test_failure_does_not_become_zero_players(self):
        with patch('server_status.fetch_status',side_effect=[OSError(),{'available':True,'clients':5}]):
            data=fetch_statuses(['abc123','def456'])
        self.assertFalse(data['abc123']['available'])
        self.assertNotIn('clients',data['abc123'])
        self.assertEqual(data['def456']['clients'],5)
    def test_page_target_uses_matching_code(self):
        self.assertEqual(page_url('6gk4e4'),'https://servers.fivem.net/servers/detail/6gk4e4')
        with self.assertRaises(ValueError):page_url('../foo')
