"""Job store queue and cancel."""

from __future__ import annotations

import unittest

from cursor_pocket.jobs import JobStore


class JobStoreTests(unittest.TestCase):
    def test_create_list_and_events(self) -> None:
        store = JobStore()
        job = store.create(prompt="hi", workspace="/tmp", workspace_name="tmp", mode="agent")
        store.append(job.id, {"kind": "assistant", "text": "hello"})
        got = store.get(job.id)
        self.assertEqual(got.events[-1]["kind"], "assistant")
        self.assertEqual(store.list()[0].id, job.id)

    def test_cancel_queued(self) -> None:
        store = JobStore()
        job = store.create(prompt="hi", workspace="/tmp", workspace_name="tmp", mode="agent")
        self.assertTrue(store.request_cancel(job.id))
        self.assertEqual(store.get(job.id).status, "canceled")
        self.assertFalse(store.request_cancel(job.id))

    def test_session_id_from_result(self) -> None:
        store = JobStore()
        job = store.create(prompt="hi", workspace="/tmp", workspace_name="tmp", mode="agent")
        store.append(job.id, {"kind": "result", "text": "done", "session_id": "abc"})
        self.assertEqual(store.get(job.id).session_id, "abc")


if __name__ == "__main__":
    unittest.main()
