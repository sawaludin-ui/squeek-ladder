import ast
import pathlib
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Load the pure planner without importing signing dependencies or touching .env.
tree = ast.parse((ROOT / 'tools/squeek.py').read_text(encoding='utf-8'))
module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_plan'], type_ignores=[])
ns = {}
exec(compile(module, 'squeek.py', 'exec'), ns)
build_plan = ns['build_plan']

class PlannerTests(unittest.TestCase):
    def test_four_tokens_carry_survivor_to_next_level(self):
        plan = build_plan([{'id': i, 'level': 1, 'next': 0} for i in range(1, 5)], 100, 3, {2: 0, 3: 0})
        self.assertEqual([m['level'] for m in plan], [1, 1, 2])
        self.assertEqual((plan[2]['survivor'], plan[2]['donor']), (1, 3))
        self.assertFalse(plan[2]['ready'])

    def test_missing_cooldown_is_not_zero(self):
        with self.assertRaises((ValueError, KeyError)):
            build_plan([{'id': i, 'level': 1, 'next': 0} for i in (1, 2)], 0, 3, {})

if __name__ == '__main__':
    unittest.main()
