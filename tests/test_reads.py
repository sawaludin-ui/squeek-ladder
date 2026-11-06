import contextlib
import importlib.util
import io
import json
import os
import pathlib
import random
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('squeek_under_test', ROOT / 'tools/squeek.py')
assert spec is not None and spec.loader is not None
squeek = importlib.util.module_from_spec(spec)
spec.loader.exec_module(squeek)
OWNER = squeek.DEFAULT_ACCOUNT


class Response(io.BytesIO):
    def __init__(self, obj):
        super().__init__(json.dumps(obj).encode())


class ApiTests(unittest.TestCase):
    def test_follows_pages_and_passes_http_timeout(self):
        pages = [{'status': 'available', 'tokens': [], 'nextCursor': 'a b'},
                 {'status': 'available', 'tokens': [], 'nextCursor': None}]
        with patch.object(squeek.urllib.request, 'urlopen', side_effect=[Response(x) for x in pages]) as call:
            self.assertEqual(squeek.api_account(OWNER), pages)
        self.assertEqual(call.call_count, 2)
        self.assertIn('cursor=a+b', call.call_args.args[0].full_url)
        self.assertEqual(call.call_args.kwargs['timeout'], 20)

    def test_cursor_cycle_and_page_cap_fail_closed(self):
        for factory in [lambda i: 'same', lambda i: str(i)]:
            n = 0
            def open_page(*args, **kwargs):
                nonlocal n
                n += 1
                return Response({'status': 'available', 'tokens': [], 'nextCursor': factory(n)})
            with patch.object(squeek.urllib.request, 'urlopen', side_effect=open_page):
                with self.assertRaisesRegex(ValueError, 'repeated|page limit'):
                    squeek.api_account(OWNER)
            self.assertIn(n, (2, 60))

    def test_unavailable_or_missing_tokens_rejects(self):
        for data in [{'status': 'available'}, {'status': 'offline', 'tokens': []}]:
            with patch.object(squeek.urllib.request, 'urlopen', return_value=Response(data)):
                with self.assertRaisesRegex(ValueError, 'incomplete|unavailable'):
                    squeek.api_account(OWNER)

    def test_duplicates_reject_and_deposited_tokens_are_excluded(self):
        t = {'tokenId': '1', 'level': 1, 'nextMergeHeight': '0', 'custody': 'wallet'}
        with patch.object(squeek, 'api_account', return_value=[{'tokens': [t, t]}]):
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                squeek.fetch_squeeks(OWNER)
        with patch.object(squeek, 'api_account', return_value=[{'tokens': [t, dict(t, tokenId='2', custody='deposited')]}]):
            result, _ = squeek.fetch_squeeks(OWNER)
            self.assertEqual(result, [{'id': 1, 'level': 1, 'next': 0}])


class PlannerInvariants(unittest.TestCase):
    def test_deterministic_random_plans_replay_without_inventing_or_reusing_tokens(self):
        rng = random.Random(17)
        for _ in range(100):
            tokens = [{'id': i, 'level': rng.randint(1, 5), 'next': rng.randint(0, 150)}
                      for i in range(1, rng.randint(2, 70))]
            plan = squeek.build_plan(tokens, 100, 5, {2: 10, 3: 20, 4: 30})
            live = {t['id']: dict(t) for t in tokens}
            mass = sum(2 ** (t['level'] - 1) for t in tokens)
            produced = set()
            for move in plan:
                a, b = live[move['survivor']], live[move['donor']]
                self.assertNotEqual(a['id'], b['id'])
                self.assertEqual((a['level'], b['level']), (move['level'], move['level']))
                if a['id'] in produced or b['id'] in produced:
                    self.assertFalse(move['ready'])
                    self.assertTrue(move['sim'])
                elif move['ready']:
                    self.assertLessEqual(max(a['next'], b['next']), 100)
                del live[b['id']]
                a['level'] += 1
                produced.add(a['id'])
            self.assertEqual(len(live), len(tokens) - len(plan))
            self.assertEqual(sum(2 ** (t['level'] - 1) for t in live.values()), mass)
            self.assertEqual(plan, squeek.build_plan(list(reversed(tokens)), 100, 5, {2: 10, 3: 20, 4: 30}))

    def test_unpaired_maximum_empty_and_cooldown_boundary(self):
        self.assertEqual(squeek.build_plan([], 0, 2, {}), [])
        self.assertEqual(squeek.build_plan([{'id': 1, 'level': 2, 'next': 0}], 0, 2, {}), [])
        t = [{'id': i, 'level': 1, 'next': 100} for i in (1, 2, 3)]
        self.assertFalse(squeek.build_plan(t, 99, 2, {})[0]['ready'])
        self.assertTrue(squeek.build_plan(t, 100, 2, {})[0]['ready'])
        self.assertEqual(len(squeek.build_plan(t, 100, 2, {})), 1)

    def test_invalid_types_and_duplicate_ids_fail_closed(self):
        base = {'id': 1, 'level': 1, 'next': 0}
        for t in [dict(base, id=True), dict(base, next=None), dict(base, level=1.5), dict(base, next=-1)]:
            with self.assertRaises(ValueError):
                squeek.build_plan([t], 100, 3, {2: 0})
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            squeek.build_plan([base, base], 100, 3, {2: 0})
        for cds in [{}, {2: -1}, {2: None}, {2: False}]:
            with self.assertRaises(ValueError):
                squeek.build_plan([], 100, 3, cds)


class SnapshotTests(unittest.TestCase):
    def snapshot(self, *, chain=11155111, balance=2, owner=OWNER, failed=None):
        calls = []
        values = {'sqkCore': squeek.CORE, 'MAXIMUM_LEVEL': 3, 'state': [9, 0, 0, 100, 0, 1, 0, False],
                  'mergesOpen': True, 'cooldownBlocks': 5, 'balanceOf': balance, 'ownerOf': owner,
                  'level': 1, 'nextMergeHeight': 0}
        class Functions:
            def __getattr__(self, name):
                def fn(*args):
                    def call(*, block_identifier):
                        self_test.assertEqual(block_identifier, 123)
                        calls.append((name, args))
                        if name == failed:
                            raise RuntimeError('read failed ' + name)
                        return values[name]
                    return types.SimpleNamespace(call=call)
                return fn
        self_test = self
        eth = types.SimpleNamespace(chain_id=chain, block_number=123,
                                    contract=lambda **kwargs: types.SimpleNamespace(functions=Functions()))
        w3 = types.SimpleNamespace(eth=eth)
        fake_web3 = types.SimpleNamespace(HTTPProvider=lambda *a, **k: None,
                                         to_checksum_address=lambda a: a)
        # Web3 is a constructor with static helpers.
        constructor = Mock(return_value=w3)
        constructor.HTTPProvider = fake_web3.HTTPProvider
        constructor.to_checksum_address = fake_web3.to_checksum_address
        indexed = [{'id': i, 'level': 1, 'next': 0} for i in (1, 2)]
        with patch.object(squeek, 'Web3', constructor), patch.object(squeek, 'fetch_squeeks', return_value=(indexed, {})):
            result = squeek.read_snapshot(OWNER)
        return result, calls

    def test_every_rpc_read_pins_one_block(self):
        result, calls = self.snapshot()
        self.assertEqual((result['height'], len(result['tokens']), result['open']), (100, 2, True))
        self.assertEqual(sum(n == 'ownerOf' for n, _ in calls), 2)

    def test_wrong_chain_owner_missing_tokens_and_read_failures_reject(self):
        for opts in [{'chain': 1}, {'balance': 3}, {'owner': '0x' + '1' * 40},
                     {'failed': 'cooldownBlocks'}, {'failed': 'level'}, {'failed': 'nextMergeHeight'},
                     {'failed': 'state'}, {'failed': 'mergesOpen'}]:
            with self.subTest(opts=opts), self.assertRaises((ValueError, RuntimeError)):
                self.snapshot(**opts)

    def test_cli_reports_read_failure_and_rejects_legacy_transaction_command(self):
        with patch.object(squeek, 'read_snapshot', side_effect=RuntimeError('offline')), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(squeek.main(['ladder']), 1)
        self.assertIn('no usable plan', err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ex:
            squeek.main(['merge'])
        self.assertEqual(ex.exception.code, 2)

    def test_cli_closed_gate_has_no_eligible_moves(self):
        s = {'tokens': [{'id': i, 'level': 1, 'next': 0} for i in (1, 2)],
             'height': 100, 'maximum': 2, 'cooldowns': {}, 'open': False, 'block': 123}
        with patch.object(squeek, 'read_snapshot', return_value=s), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(squeek.main(['ladder']), 0)
        self.assertIn('0 eligible at snapshot', out.getvalue())
        self.assertIn('GATE CLOSED', out.getvalue())


class SiteBuildTests(unittest.TestCase):
    def test_real_builder_emits_html_and_preserves_project_identity(self):
        source = (ROOT / 'build_site.py').read_text(encoding='utf8')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            fake_path = pathlib.Path(tmp) / 'build_site.py'
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, str(fake_path), 'exec'), {'__file__': str(fake_path), '__name__': '__main__'})
            html = fake_path.with_name('planner.html').read_text(encoding='utf8')
        self.assertIn('502c8855-e4e0-4067-bf83-d2de88597fa3', html)
        self.assertIn('Read-only Sepolia planner', html)
        self.assertIn('transaction execution disabled', html)
        self.assertNotIn('getSigner(', html)
        self.assertNotIn('innerHTML = kind', html)
        self.assertIn('--acid:#c8f751', html)


if __name__ == '__main__':
    unittest.main()
