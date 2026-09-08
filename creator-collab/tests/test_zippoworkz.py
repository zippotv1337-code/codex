from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from creator_ops.asset_import import LocalAssetImportService
from creator_ops.cli import build_pipeline
from creator_ops.review import ReviewDashboardService
from creator_ops.web import create_server


class ZippoWorkzTests(unittest.TestCase):
    def test_canonical_views_and_persistent_story_http_flow(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = root / 'review.db'
            pipeline = build_pipeline(db)
            pipeline.initialize()
            reviews = ReviewDashboardService(pipeline)
            reviews.ensure_date(date(2026, 9, 5))
            sources = []
            for i in range(5):
                image = root / f'{i}.png'
                image.write_bytes(b'\x89PNG\r\n\x1a\n' + bytes([i]))
                sources.append(image)
            LocalAssetImportService(pipeline, root).import_files('leona-voss', date(2026, 9, 5), sources)
            server = create_server(db, port=0, asset_root=root)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                for route in ('/', '/stories', '/archive', '/analytics', '/revenue', '/offer', '/control', '/collections', '/top3', '/engagement'):
                    with urlopen(base + route) as response:
                        html = response.read().decode()
                    self.assertIn('<title>ZippoWorkz', html)
                    self.assertEqual(html.count('aria-label="Hauptnavigation"'), 1)
                    self.assertIn('Heute / Review', html)
                    self.assertIn('Fiverr / Revenue', html)
                    self.assertIn('Planung / Queue', html)
                def stories():
                    with urlopen(base + '/api/stories') as response:
                        result = json.load(response)
                        self.assertEqual(result['review_schema'], 'story-review-v1')
                        return result['items']
                item = next(p for p in stories() if p['creator_slug'] == 'leona-voss')
                content_id = item['content_id']
                original_caption = pipeline.db.scalar('SELECT caption FROM platform_variants WHERE content_id=?', (content_id,))
                fields = {'cta':'Kurze Pause am Fenster?', 'highlight':'Berlin',
                          'frames':[{'kind':'TEASER', 'copy':'Der erste Kaffee.', 'interaction':''} for _ in item['frames']]}
                actions = [('edit', fields, 'READY_FOR_OWNER_REVIEW'), ('approve', {}, 'APPROVED'),
                           ('plan', {'planned_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}, 'LOCAL_PLANNED'),
                           ('pause', {}, 'PAUSED'), ('change', {}, 'CHANGE_REQUESTED'), ('reject', {}, 'REJECTED')]
                for action, fields, status in actions:
                    body = urlencode({'fields':json.dumps(fields)}).encode()
                    with urlopen(Request(f'{base}/api/stories/{content_id}/{action}', data=body,
                                         headers={'Content-Type':'application/x-www-form-urlencoded'})) as response:
                        self.assertFalse(json.load(response)['external_action'])
                    self.assertEqual(next(p for p in stories() if p['content_id']==content_id)['status'], status)
                self.assertEqual(pipeline.db.scalar('SELECT COUNT(*) FROM publish_queue'), 0)
                self.assertEqual(pipeline.db.scalar('SELECT COUNT(*) FROM publications'), 0)
                self.assertEqual(pipeline.db.scalar('SELECT caption FROM platform_variants WHERE content_id=?', (content_id,)), original_caption)
                self.assertEqual(pipeline.db.scalar('PRAGMA integrity_check'), 'ok')
                self.assertEqual(pipeline.db.all('PRAGMA foreign_key_check'), [])
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
