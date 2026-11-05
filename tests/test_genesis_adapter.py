# Python unittest · public Genesis adapter · fixed upstream and fail-closed validation.
import importlib.util
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'site/api/genesis.py'
SPEC = importlib.util.spec_from_file_location('genesis_adapter_test', SOURCE)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class AdapterTests(unittest.TestCase):
    def test_public_profile(self):
        self.assertEqual(adapter.upstream_url('/api/genesis?resource=profile&code=pbsm54mn'),
                         adapter.UPSTREAM + '/profiles/pbsm54mn')

    def test_fixed_catalogue_and_leaderboard(self):
        for resource in ('aura/badges', 'leaderboard'):
            self.assertEqual(adapter.upstream_url('/api/genesis?resource=' + resource),
                             adapter.UPSTREAM + '/' + resource)

    def test_reject_arbitrary_urls(self):
        for resource in ('https://example.com', '//127.0.0.1', 'auth/challenge', '../admin', ''):
            with self.subTest(resource=resource), self.assertRaises(ValueError):
                adapter.upstream_url('/api/genesis?resource=' + resource)

    def test_reject_path_injection_and_missing_code(self):
        for code in ('', '../admin', 'a/b', 'x?private=1', 'x' * 65):
            with self.subTest(code=code), self.assertRaises(ValueError):
                adapter.upstream_url('/api/genesis?resource=profile&code=' + code)


if __name__ == '__main__':
    unittest.main()
