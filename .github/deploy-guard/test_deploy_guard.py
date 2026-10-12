"""Tests that only a first-attempt push to main deploys (run: python3 -m unittest discover -s .github/deploy-guard).

Every later job in deploy.yml chains off deploy-staging through `needs`, so
its `if:` is the whole gate between a CI completion and a production deploy or
rollback. build-drift dispatches CI on main daily; a dispatch or a re-run must
never get past this gate.
"""

import pathlib
import re
import unittest

import yaml

DEPLOY_YML = pathlib.Path(__file__).resolve().parents[1] / "workflows" / "deploy.yml"

TOKEN = re.compile(
    r"\s*(?:(?P<str>'[^']*')|(?P<num>\d+)|(?P<op>==|!=|&&|\|\||!|\(|\))|(?P<name>[A-Za-z_][\w.-]*))"
)


def evaluate(expression, context):
    """Evaluate the GitHub expression subset the guard uses against a context dict.

    Unknown properties resolve to None, as they do on GitHub.
    """

    def lookup(path):
        value = context
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value

    python, pos = [], 0
    expression = expression.strip()
    while pos < len(expression):
        m = TOKEN.match(expression, pos)
        if not m or m.end() == pos:
            raise ValueError("unsupported expression syntax at: %r" % expression[pos:])
        pos = m.end()
        if m["str"]:
            python.append(repr(m["str"][1:-1]))
        elif m["num"]:
            python.append(m["num"])
        elif m["op"]:
            python.append({"&&": " and ", "||": " or ", "!": " not "}.get(m["op"], m["op"]))
        else:
            python.append("lookup(%r)" % m["name"])
    return bool(eval("".join(python), {"__builtins__": {}}, {"lookup": lookup}))


def ci_completion(**overrides):
    run = {
        "conclusion": "success",
        "event": "push",
        "run_attempt": 1,
        "head_branch": "main",
        "head_repository": {"full_name": "alexsiri7/kindred"},
    }
    run.update(overrides)
    return {
        "github": {
            "event_name": "workflow_run",
            "repository": "alexsiri7/kindred",
            "event": {"workflow_run": run},
        }
    }


class DeployStagingGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow = yaml.safe_load(DEPLOY_YML.read_text())
        cls.guard = workflow["jobs"]["deploy-staging"]["if"]

    def deploys(self, context):
        return evaluate(self.guard, context)

    def test_successful_push_to_main_deploys(self):
        self.assertTrue(self.deploys(ci_completion()))

    def test_dispatched_ci_run_does_not_deploy(self):
        self.assertFalse(self.deploys(ci_completion(event="workflow_dispatch")))

    def test_rerun_of_push_ci_run_does_not_deploy(self):
        self.assertFalse(self.deploys(ci_completion(run_attempt=2)))

    def test_pull_request_ci_run_does_not_deploy(self):
        self.assertFalse(self.deploys(ci_completion(event="pull_request")))

    def test_fork_branch_named_main_does_not_deploy(self):
        fork = {"full_name": "someone/kindred"}
        self.assertFalse(self.deploys(ci_completion(head_repository=fork)))

    def test_failed_ci_run_does_not_deploy(self):
        self.assertFalse(self.deploys(ci_completion(conclusion="failure")))

    def test_manual_deploy_dispatch_from_main_deploys(self):
        context = {"github": {"event_name": "workflow_dispatch", "ref": "refs/heads/main"}}
        self.assertTrue(self.deploys(context))

    def test_manual_deploy_dispatch_from_other_branch_does_not_deploy(self):
        context = {"github": {"event_name": "workflow_dispatch", "ref": "refs/heads/feature"}}
        self.assertFalse(self.deploys(context))


if __name__ == "__main__":
    unittest.main()
