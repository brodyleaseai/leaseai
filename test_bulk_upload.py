"""Bulk upload must keep every selected file and continue after a failure."""

import unittest

from bulk_upload import (
    drain_bulk_queue,
    next_bulk_job,
    process_one_job,
    queue_bulk_jobs,
    snapshot_uploaded_files,
)
from extraction_timeout import ExtractionTimeoutError, run_extraction_with_timeout


class FakeFile:
    def __init__(self, name, data):
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self):
        return self._data


class SnapshotTests(unittest.TestCase):
    def test_keeps_all_three_files(self):
        files = [
            FakeFile("lease-a.pdf", b"%PDF-a"),
            FakeFile("lease-b.pdf", b"%PDF-b"),
            FakeFile("lease-c.pdf", b"%PDF-c"),
        ]
        jobs = snapshot_uploaded_files(files)
        self.assertEqual([job["filename"] for job in jobs], [
            "lease-a.pdf",
            "lease-b.pdf",
            "lease-c.pdf",
        ])
        self.assertEqual(jobs[1]["data"], b"%PDF-b")


class QueueTests(unittest.TestCase):
    def test_middle_failure_does_not_drop_the_third_lease(self):
        session = {}
        files = [
            FakeFile("one.pdf", b"1"),
            FakeFile("two.pdf", b"2"),
            FakeFile("three.pdf", b"3"),
        ]
        queue_bulk_jobs(session, files, "client-1")
        calls = []

        def process_job(job):
            calls.append(job["filename"])
            if job["filename"] == "two.pdf":
                return {
                    "filename": job["filename"],
                    "status": "error",
                    "lease_id": None,
                    "field_count": 0,
                    "message": "GPT-4 extraction failed: 429",
                }
            return {
                "filename": job["filename"],
                "status": "success",
                "lease_id": f"id-{job['filename']}",
                "field_count": 84,
                "message": "Extracted 84 fields",
            }

        results = drain_bulk_queue(session, process_job)
        self.assertEqual(calls, ["one.pdf", "two.pdf", "three.pdf"])
        self.assertEqual(len(results), 3)
        self.assertEqual([row["status"] for row in results], ["success", "error", "success"])
        self.assertIsNone(next_bulk_job(session))


class ProcessJobTests(unittest.TestCase):
    def test_uses_a_fresh_supabase_client_per_job(self):
        created = []

        class Pipeline:
            def process_lease(self, **kwargs):
                return "lease-1", {"A": {"value": "1"}}

        job = {"filename": "Harbourview.pdf", "data": b"%PDF", "client_id": "c1"}
        result = process_one_job(
            job,
            supabase_factory=lambda: created.append("sb") or "client",
            pipeline_factory=Pipeline,
            run_extract=lambda pipeline, **kwargs: pipeline.process_lease(**kwargs),
            increment_usage=lambda sb, client_id: None,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["lease_id"], "lease-1")
        self.assertEqual(created, ["sb"])

    def test_failed_extract_is_an_error_result(self):
        class Pipeline:
            pass

        result = process_one_job(
            {"filename": "bad.pdf", "data": b"x", "client_id": "c1"},
            supabase_factory=lambda: "sb",
            pipeline_factory=Pipeline,
            run_extract=lambda pipeline, **kwargs: (_ for _ in ()).throw(RuntimeError("429 rate limit")),
            increment_usage=lambda sb, client_id: (_ for _ in ()).throw(AssertionError("should not increment")),
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("429", result["message"])


class OpenAIRetryTests(unittest.TestCase):
    def test_retries_rate_limit_then_succeeds(self):
        from extraction_pipeline import LeaseExtractionPipeline

        calls = {"n": 0}

        class FakeCompletions:
            def create(self, **kwargs):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise RuntimeError("Error code: 429 - rate limit exceeded")

                class Message:
                    content = '{"Tenant Legal Name": {"value": "Acme", "confidence": "HIGH"}}'

                class Choice:
                    message = Message()

                class Response:
                    choices = [Choice()]

                return Response()

        pipeline = LeaseExtractionPipeline.__new__(LeaseExtractionPipeline)
        pipeline.lease_fields = ["Tenant Legal Name"]
        pipeline.client = type("Client", (), {})()
        pipeline.client.chat = type("Chat", (), {})()
        pipeline.client.chat.completions = FakeCompletions()

        result = pipeline.extract_fields_with_gpt4("A commercial lease.", None, None)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(result["Tenant Legal Name"]["value"], "Acme")


class TimeoutHelperTests(unittest.TestCase):
    def test_three_jobs_all_return(self):
        class Pipeline:
            def process_lease(self, **kwargs):
                return kwargs["filename"], {}

        results = [
            run_extraction_with_timeout(Pipeline(), filename=name)
            for name in ("a.pdf", "b.pdf", "c.pdf")
        ]
        self.assertEqual([row[0] for row in results], ["a.pdf", "b.pdf", "c.pdf"])

    def test_timeout_raises(self):
        import os
        import time

        class Pipeline:
            def process_lease(self, **kwargs):
                time.sleep(0.3)
                return "late", {}

        previous = os.environ.get("EXTRACTION_TIMEOUT_SECONDS")
        os.environ["EXTRACTION_TIMEOUT_SECONDS"] = "0"
        try:
            with self.assertRaises(ExtractionTimeoutError):
                run_extraction_with_timeout(Pipeline())
        finally:
            if previous is None:
                os.environ.pop("EXTRACTION_TIMEOUT_SECONDS", None)
            else:
                os.environ["EXTRACTION_TIMEOUT_SECONDS"] = previous


if __name__ == "__main__":
    unittest.main()
