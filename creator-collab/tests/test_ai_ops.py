from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from creator_ops.ai_ops import AiOpsService, TASKS
from creator_ops.database import CreatorDatabase
from creator_ops.local_ai_runtime import LocalWorker, PauseRequested, safe_sync, validate_policy
from creator_ops.web import create_server


class AiOpsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'Workspace' / 'codex_ingest' / 'creator-collab'
        self.project.mkdir(parents=True)
        self.db = CreatorDatabase(self.project / 'data' / 'review_dashboard.db')
        self.db.initialize()
        self.service = AiOpsService(self.db, self.project, self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_schema_five_no_extra_database_and_no_fabricated_agents(self):
        state = self.service.snapshot()
        self.assertEqual(self.db.schema_version(), 5)
        self.assertEqual([a['status'] for a in state['agents']], ['OFFLINE'] * 3)
        self.assertIsNotNone(state['data_notice'])
        self.assertEqual(state['external_actions'], 'NONE')
        self.assertEqual(len(list(self.root.rglob('*.db'))), 1)

    def test_pause_resume_persists_and_rejects_external_commands(self):
        self.service.command('pause')
        fresh = AiOpsService(self.db, self.project, self.root)
        self.assertEqual(fresh.control(), 'PAUSED')
        with self.assertRaises(PauseRequested):
            LocalWorker(fresh, activity=lambda: False).tick()
        fresh.command('resume')
        self.assertEqual(fresh.control(), 'RUN')
        with self.assertRaises(ValueError):
            fresh.command('publish')

    def test_owner_activity_pauses_without_consuming_attempt(self):
        worker = LocalWorker(self.service, activity=lambda: True)
        with self.assertRaises(PauseRequested):
            worker.tick()
        self.assertEqual(self.service.snapshot()['tasks'][0]['attempts'], 0)

    def test_resume_skips_completed_steps_and_has_real_result(self):
        worker = LocalWorker(self.service, activity=lambda: False)
        self.assertTrue(worker.tick())
        self.assertEqual(self.service.read('task.health')['result']['integrity'], 'ok')
        with patch.object(worker, 'execute', return_value={'exit_code': 0}) as execute:
            worker.tick()
        execute.assert_called_once_with('tests')
        self.assertEqual(self.service.read('task.health')['attempts'], 1)
        self.assertTrue((self.root / 'Handoff' / 'LOCAL_AI_RESULT.md').is_file())

    def test_failed_task_blocked_no_automatic_retry_and_no_secret_error(self):
        worker = LocalWorker(self.service, activity=lambda: False)
        with patch.object(worker, 'execute', side_effect=RuntimeError('token=private-value')):
            worker.tick()
        self.assertEqual(self.service.read('task.health')['status'], 'BLOCKED')
        self.assertFalse(worker.tick())
        self.assertNotIn('private-value', json.dumps(self.service.snapshot()))

    def test_pause_mid_step_checkpoints_and_resumes_same_task(self):
        worker = LocalWorker(self.service, activity=lambda: False)
        with patch.object(worker, 'execute', side_effect=PauseRequested):
            with self.assertRaises(PauseRequested):
                worker.tick()
        self.assertEqual(self.service.read('task.health')['status'], 'PAUSED')
        self.assertEqual(self.service.read('task.health')['attempts'], 0)
        worker.tick()
        self.assertEqual(self.service.read('task.health')['status'], 'DONE')

    def test_second_worker_cannot_take_existing_lease(self):
        worker = LocalWorker(self.service, activity=lambda: False)
        token = worker.coordinator._acquire(datetime.now(UTC))
        try:
            with patch.object(worker, 'tick') as tick:
                self.assertEqual(worker.run(), 0)
                tick.assert_not_called()
        finally:
            worker.coordinator._release(token)

    def test_dashboard_start_resets_stopped_and_uses_verified_model(self):
        self.service.command('stop')
        with patch('creator_ops.ai_ops.subprocess.Popen') as popen:
            self.service.start_local_worker()
        self.assertEqual(self.service.control(), 'RUN')
        args = popen.call_args.args[0]
        self.assertIn('--model', args)
        self.assertEqual(args[args.index('--model') + 1], 'qwen3:8b')

    def test_stale_heartbeat_is_offline(self):
        self.service.agent('codex', 'WORKING', task='integration')
        state = self.service.snapshot(datetime.now(UTC) + timedelta(minutes=3))
        self.assertEqual(state['agents'][0]['status'], 'OFFLINE')

    def test_archive_fallback_never_downloads_or_deletes(self):
        sentinel = self.project / 'owner.txt'
        sentinel.write_text('preserve', encoding='utf-8')
        runner = Mock(side_effect=AssertionError('no git for archive'))
        self.assertEqual(safe_sync(self.project, runner)['status'], 'DEGRADED')
        self.assertEqual(sentinel.read_text(), 'preserve')
        runner.assert_not_called()

    def test_git_timeout_is_bounded_and_noninteractive(self):
        (self.project.parent / '.git').mkdir()
        runner = Mock(side_effect=subprocess.TimeoutExpired('git', 12))
        state = safe_sync(self.project, runner)
        self.assertEqual(state['reason'], 'GIT_TIMEOUT_LOCAL_FALLBACK')
        self.assertEqual(runner.call_args.kwargs['timeout'], 12)
        self.assertEqual(runner.call_args.kwargs['env']['GIT_TERMINAL_PROMPT'], '0')

    def test_dirty_worktree_kept_without_fetch(self):
        (self.project.parent / '.git').mkdir()
        runner = Mock(side_effect=[Mock(returncode=0, stdout='a'*40), Mock(returncode=0, stdout=' M owner.md')])
        self.assertEqual(safe_sync(self.project, runner)['reason'], 'LOCAL_CHANGES_PRESERVED')
        self.assertEqual(runner.call_count, 2)

    def test_model_capacity_no_generation_if_busy(self):
        worker = LocalWorker(self.service, activity=lambda: False)
        with patch.object(worker, 'local_json', side_effect=[{'models':[{'name':'qwen2.5-coder:3b'}]}, {'models':[{'name':'other'}]}]):
            with self.assertRaisesRegex(ValueError, 'MODEL_CAPACITY_BUSY'):
                worker.summarize()

    def test_worker_bounded_idle_stops_releases_lease(self):
        for task in TASKS:
            self.service.task(task['id'], 'DONE', attempts=1)
        worker = LocalWorker(self.service, activity=lambda: False)
        self.assertEqual(worker.run(watch_seconds=30), 0)
        self.assertEqual(self.db.scalar('SELECT COUNT(*) FROM run_leases'), 0)
        self.assertEqual(self.service.snapshot()['agents'][1]['status'], 'OFFLINE')

    def test_policy_fails_closed(self):
        folder = self.root / '_system'
        folder.mkdir()
        path = folder / 'PERMISSIONS_POLICY.json'
        path.write_text(json.dumps({'root':str(self.root),'mode':'LOCAL_SAFE_ONLY','platform_actions':True}))
        with self.assertRaisesRegex(ValueError, 'POLICY_FORBIDDEN_CAPABILITY'):
            validate_policy(self.root)

    def test_stop_before_work_releases_and_preserves_queue(self):
        self.service.command('stop')
        worker = LocalWorker(self.service, activity=lambda: False)
        self.assertEqual(worker.run(watch_seconds=30), 0)
        self.assertEqual(self.service.snapshot()['tasks'][0]['status'], 'NEXT')
        self.assertEqual(self.db.scalar('SELECT COUNT(*) FROM run_leases'), 0)

    def test_model_uses_installed_fallback_without_download(self):
        worker = LocalWorker(self.service, activity=lambda: False)
        with patch.object(worker, 'local_json', side_effect=[{'models':[{'name':'qwen3:8b'}]},{'models':[{'name':'busy'}]}]):
            with self.assertRaisesRegex(ValueError, 'MODEL_CAPACITY_BUSY'):
                worker.summarize()
        self.assertEqual(worker.model, 'qwen3:8b')

    def test_http_ui_and_commands_existing_auth_csrf(self):
        server = create_server(self.db.path, port=0, asset_root=self.project, auth_password='test-only-long-password')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(base + '/api/ai-ops', timeout=3)
            self.assertEqual(error.exception.code, 401)
            session = server.RequestHandlerClass.auth.authenticate('test-only-long-password','local-test')
            cookies = f'creator_ops_session={session.token}; creator_ops_csrf={session.csrf}'
            request = Request(base+'/api/ai-ops/pause',method='POST',headers={'Cookie':cookies})
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=3)
            self.assertEqual(error.exception.code, 403)
            request.add_header('X-CSRF-Token', session.csrf)
            with urlopen(request, timeout=3) as response:
                self.assertEqual(json.load(response)['control'], 'PAUSED')
            with urlopen(Request(base+'/ai-ops',headers={'Cookie':cookies}),timeout=3) as response:
                self.assertIn('Lokalen Lauf starten',response.read().decode())
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
