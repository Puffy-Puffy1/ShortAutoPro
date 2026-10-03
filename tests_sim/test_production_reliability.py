"""Behavioral regressions for production ownership, resume and recovery."""
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

import main as pipeline
import media_stage_runtime as media
import resume_short_runtime as resume
import storage_manager as storage
import subprocess_guard as guard


class ProductionOwnershipTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {})
        environment.start()
        self.addCleanup(environment.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.locks = self.base / '.locks' / 'runs'
        patcher = patch.object(pipeline, 'LOCK_DIR', self.locks)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_waiting_descriptor_cannot_split_lock_ownership(self):
        with pipeline.RunLock('one') as first:
            waiter = first.path.open('a+')
        self.addCleanup(waiter.close)
        fcntl.flock(waiter, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with self.assertRaises(RuntimeError):
            with pipeline.RunLock('one'):
                self.fail('two owners acquired one production')

    def test_storage_probe_preserves_waiting_descriptor(self):
        self.locks.mkdir(parents=True)
        path = self.locks / 'one.lock'
        with path.open('a+') as waiter:
            self.assertFalse(storage._held_lock(path))
            fcntl.flock(waiter, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertTrue(storage._held_lock(path))

    def test_failed_contender_closes_its_handle(self):
        with pipeline.RunLock('one'):
            second = pipeline.RunLock('one')
            with self.assertRaises(RuntimeError):
                second.__enter__()
            self.assertIsNone(second.handle)

    def test_lock_is_reusable_after_exception(self):
        with self.assertRaises(ValueError):
            with pipeline.RunLock('one'):
                raise ValueError('stage failed')
        with pipeline.RunLock('one'):
            self.assertTrue(storage._held_lock(self.locks / 'one.lock'))

    def test_unreadable_lock_is_conservatively_active(self):
        with patch.object(Path, 'open', side_effect=PermissionError):
            self.assertTrue(storage._held_lock(self.locks / 'one.lock'))

    def test_resume_contention_does_not_fail_active_production(self):
        with pipeline.RunLock('one'), patch.object(resume.evo, 'finish_production') as finish:
            with patch.object(resume, 'boundary') as boundary:
                self.assertEqual(resume.resume('one'), 1)
            boundary.assert_not_called()
            finish.assert_not_called()


class ResumeReliabilityTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {})
        environment.start()
        self.addCleanup(environment.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        for module in (pipeline, resume):
            patcher = patch.object(module, 'BASE', self.base)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(pipeline, 'STATE_DIR', self.base / '.sap_state')
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.base / 'main.py').touch()

    def test_full_resume_reuses_requested_id_with_existing_artifacts(self):
        folder = self.base / 'roteiros'
        folder.mkdir()
        (folder / 'scene_map_existing.json').write_text('{}')
        def launch(command, **kwargs):
            self.assertEqual(command[-2:], ['run', '--reuse-short-id'])
            with patch.dict(os.environ, kwargs['env']):
                self.assertEqual(
                    pipeline.allocate_id(reuse_existing=True),
                    'existing',
                )
            return subprocess.CompletedProcess(command, 0)
        with patch.object(resume, 'run_group', side_effect=launch):
            self.assertEqual(resume.full_rerun('existing'), 0)

    def plans(self, score=90):
        folder = self.base / 'roteiros'
        folder.mkdir(exist_ok=True)
        (folder / 'pro_edit_plan_one.json').write_text(json.dumps({
            'schema_version': 'render-plan-v2', 'short_id': 'one', 'scenes': [{}] * 12}))
        manifests = self.base / 'manifests'
        manifests.mkdir(exist_ok=True)
        (manifests / 'media_one.json').write_text(json.dumps({
            'schema_version': 'media-manifest-v2',
            'short_id': 'one',
            'immutable': True,
            'scenes': [{'scene': i, 'asset': {'validated': True, 'checksum_sha256': f'sha-{i}'}} for i in range(1, 13)]
        }))
        for name in ('retention', 'sound_design', 'multi_asset', 'visual_score', 'visual_continuity'):
            (folder / f'{name}_one.json').write_text(json.dumps({'retention_score': score, 'padding': 'enough bytes'}))

    def test_malformed_v2_manifest_cannot_crash_or_pass(self):
        self.plans()
        manifest = self.base / 'manifests' / 'media_one.json'
        for payload in (
            {'schema_version': 'wrong', 'short_id': 'one', 'immutable': True, 'scenes': [{}] * 12},
            {'schema_version': 'media-manifest-v2', 'short_id': 'other', 'immutable': True, 'scenes': [{}] * 12},
            {'schema_version': 'media-manifest-v2', 'short_id': 'one', 'immutable': False, 'scenes': [{}] * 12},
        ):
            with self.subTest(payload=payload):
                manifest.write_text(json.dumps(payload))
                self.assertFalse(resume.consolidation_plan_ok('one'))
        self.plans()

    def test_valid_v2_checkpoint_is_accepted(self):
        self.plans()
        with patch.dict(os.environ, {'SHORT_QTD_CENAS': '12'}):
            self.assertTrue(resume.consolidation_plan_ok('one'))

    def test_large_but_corrupt_v2_manifest_is_not_a_checkpoint(self):
        self.plans()
        (self.base / 'manifests' / 'media_one.json').write_text('not json ' * 20)
        self.assertFalse(resume.consolidation_plan_ok('one'))

    def test_audio_does_not_allow_resume_with_missing_media(self):
        with contextlib.ExitStack() as stack:
            values = dict(render_ok=False, final_ok=False, consolidation_plan_ok=True,
                          assembly_ok=False, audio_ok=True, captions_ok=True,
                          supervisor_ok=True, media_ok=False, scene_count=12)
            for name, value in values.items():
                stack.enter_context(patch.object(resume, name, return_value=value))
            self.assertEqual(resume.boundary('one'), 'full')

    def test_valid_assembly_can_resume_after_original_media_cleanup(self):
        with contextlib.ExitStack() as stack:
            values = dict(render_ok=False, final_ok=False, consolidation_plan_ok=True,
                          assembly_ok=True, audio_ok=True, captions_ok=True, media_ok=False)
            for name, value in values.items():
                stack.enter_context(patch.object(resume, name, return_value=value))
            self.assertEqual(resume.boundary('one'), 'post_assembly')

    def test_duplicate_media_files_cannot_replace_missing_scenes(self):
        folder = self.base / 'imagens' / 'short_one'
        folder.mkdir(parents=True)
        reports = self.base / 'roteiros'
        reports.mkdir()
        (reports / 'media_quality_one.json').write_text('{"status":"PASS"}')
        for scene in range(1, 7):
            for extension in ('jpg', 'mp4'):
                (folder / f'scene_{scene}.{extension}').write_bytes(b'x' * 2000)
        with patch.dict(os.environ, {'SHORT_QTD_CENAS': '12'}):
            self.assertFalse(resume.media_ok('one'))
            for scene in range(7, 13):
                (folder / f'scene_{scene}.jpg').write_bytes(b'x' * 2000)
            self.assertTrue(resume.media_ok('one'))

    def test_each_partial_boundary_finishes_without_rerunning_previous_stages(self):
        with patch.object(pipeline, 'LOCK_DIR', self.base / '.locks' / 'runs'):
            for point in ('post_planning', 'post_audio', 'post_captions', 'post_assembly', 'post_render'):
                with self.subTest(point=point), contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(resume, 'boundary', return_value=point))
                    run = stack.enter_context(patch.object(resume, 'run_python', return_value=0))
                    tail = stack.enter_context(patch.object(resume, 'render_tail'))
                    stack.enter_context(patch.object(resume, 'render_ok', return_value=True))
                    stack.enter_context(patch.object(resume, 'final_gates', return_value=0))
                    stack.enter_context(patch.object(resume, 'final_ok', return_value=True))
                    stack.enter_context(patch.object(resume, 'copy_download', return_value='video.mp4'))
                    finish = stack.enter_context(patch.object(resume.evo, 'finish_production'))
                    self.assertEqual(resume.resume('one'), 0)
                    scripts = [call.args[2] for call in run.call_args_list]
                    self.assertEqual('audio.py' in scripts, point == 'post_planning')
                    self.assertEqual('legenda_dinamica.py' in scripts, point in {'post_planning', 'post_audio'})
                    self.assertEqual(tail.called, point in {'post_planning', 'post_audio', 'post_captions', 'post_assembly'})
                    finish.assert_called_once_with('SUCCESS', 'one')

    def test_full_resume_releases_parent_lock_before_launching_child(self):
        with patch.object(pipeline, 'LOCK_DIR', self.base / '.locks' / 'runs'):
            def launch(sid):
                with pipeline.RunLock(sid):
                    return 0
            with patch.object(resume, 'boundary', return_value='full'), patch.object(resume, 'full_rerun', side_effect=launch):
                self.assertEqual(resume.resume('one'), 0)


class MediaRecoveryTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {})
        environment.start()
        self.addCleanup(environment.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.report = self.base / 'report.json'
        self.script = self.base / 'midia.py'
        self.script.touch()
        scene_dir = self.base / 'roteiros'
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / 'scene_map_one.json').write_text(json.dumps({
            'scenes': [
                {'scene_id': f'scene_{n:02d}', 'scene': n}
                for n in range(1, 13)
            ]
        }))
        for key, value in dict(BASE=self.base, REPORT=self.report, SID='one', MIDIA=self.script).items():
            patcher = patch.object(media, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_report(self, missing):
        temp = self.base / 'report.tmp'
        temp.write_text(json.dumps({'missing_scenes': [{'scene': n} for n in missing],
                                    'total': 12-len(missing), 'expected': 12}))
        temp.replace(self.report)

    def test_runtime_delegates_to_v2_engine(self):
        engine = self.base / "media_engine_v2.py"
        engine.write_text("pass\n", encoding="utf-8")
        with patch.object(media, "run_group", return_value=Mock(returncode=0)) as run:
            self.assertEqual(media.main(), 0)
        command = run.call_args.args[0]
        self.assertIn("media_engine_v2.py", str(command))
        self.assertIn("--short-id", command)
        self.assertIn("one", command)

    def test_runtime_propagates_v2_failure(self):
        engine = self.base / "media_engine_v2.py"
        engine.write_text("pass\n", encoding="utf-8")
        with patch.object(media, "run_group", return_value=Mock(returncode=7)):
            self.assertEqual(media.main(), 7)

    def test_runtime_timeout_keeps_timeout_contract(self):
        engine = self.base / "media_engine_v2.py"
        engine.write_text("pass\n", encoding="utf-8")
        with patch.object(media, "run_group", side_effect=subprocess.TimeoutExpired("media_engine_v2.py", 10)):
            self.assertEqual(media.main(), 124)

    def test_runtime_does_not_retry_without_explicit_v2_controller(self):
        engine = self.base / "media_engine_v2.py"
        engine.write_text("pass\n", encoding="utf-8")
        with patch.object(media, "run_group", return_value=Mock(returncode=1)) as run:
            self.assertEqual(media.main(), 1)
        self.assertEqual(run.call_count, 1)

    def test_budget_counts_media_only_not_placeholders_or_duplicate_formats(self):

        folder = self.base / 'imagens' / 'short_one'
        folder.mkdir(parents=True)
        for name, size in [('scene_1.jpg', 2000), ('scene_1.mp4', 2000), ('scene_2.json', 2000),
                           ('scene_3.jpg', 0), ('scene_99.jpg', 2000), ('scene_4.part', 2000)]:
            (folder / name).write_bytes(b'x' * size)
        with patch.dict(os.environ, {'SHORT_QTD_CENAS': '12'}):
            self.assertEqual(media.current_completed_hint(), 1)


class ProcessCleanupTests(unittest.TestCase):
    def test_interrupt_terminates_child_group_before_propagating(self):
        proc = Mock(pid=123456)
        proc.communicate.side_effect = [KeyboardInterrupt(), (None, None)]
        with patch.object(guard.subprocess, 'Popen', return_value=proc), patch.object(guard.os, 'killpg') as kill:
            with self.assertRaises(KeyboardInterrupt):
                guard.run_group(['dummy'])
        self.assertEqual(kill.call_args_list[0].args, (123456, signal.SIGTERM))
        self.assertEqual(kill.call_args_list[-1].args, (123456, signal.SIGKILL))

    def test_timeout_preserves_captured_output(self):
        with self.assertRaises(subprocess.TimeoutExpired) as error:
            guard.run_group([sys.executable, '-c', 'import time; print("checkpoint", flush=True); time.sleep(30)'],
                            capture_output=True, text=True, timeout=0.5)
        self.assertIn('checkpoint', error.exception.output)

    @unittest.skipUnless(Path('/proc').is_dir(), 'Linux process state required')
    def test_stubborn_descendant_dies_even_when_leader_exits_on_term(self):
        with tempfile.TemporaryDirectory() as temp:
            pid_path = Path(temp) / 'child.pid'
            child = 'import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path(%r).write_text(str(os.getpid())); time.sleep(30)' % str(pid_path)
            leader = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",%r]); time.sleep(30)' % child
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    guard.run_group([sys.executable, '-c', leader], timeout=1)
                pid = int(pid_path.read_text())
                for _ in range(40):
                    path = Path(f'/proc/{pid}/stat')
                    if not path.exists() or path.read_text().split()[2] == 'Z':
                        break
                    time.sleep(0.025)
                else:
                    self.fail('descendant remains alive after timeout')
            finally:
                if pid_path.exists():
                    try:
                        os.kill(int(pid_path.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_successful_command_and_nonzero_error_keep_contract(self):
        result = guard.run_group([sys.executable, '-c', 'print("ok")'], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), 'ok')
        with self.assertRaises(subprocess.CalledProcessError) as error:
            guard.run_group([sys.executable, '-c', 'raise SystemExit(7)'], check=True)
        self.assertEqual(error.exception.returncode, 7)


if __name__ == '__main__':
    unittest.main()
