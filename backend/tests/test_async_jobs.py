import unittest

from meetmanager.v1 import meet_manager_pb2 as pb2
from server import JobManager


class TestJobManager(unittest.TestCase):
    def setUp(self):
        self.job_manager = JobManager(max_jobs=5)

    def test_create_job(self):
        job_id = self.job_manager.create_job()
        self.assertIsNotNone(job_id)
        job = self.job_manager.get_job(job_id)
        self.assertEqual(job["status"], pb2.JOB_STATUS_PENDING)
        self.assertEqual(job["progress"], 0.0)

    def test_update_job(self):
        job_id = self.job_manager.create_job()
        self.job_manager.update_job(job_id, status=pb2.JOB_STATUS_PROCESSING, progress=0.5, message="Halfway there")
        job = self.job_manager.get_job(job_id)
        self.assertEqual(job["status"], pb2.JOB_STATUS_PROCESSING)
        self.assertEqual(job["progress"], 0.5)
        self.assertEqual(job["message"], "Halfway there")

    def test_job_eviction(self):
        # Create 5 jobs (max capacity)
        job_ids = [self.job_manager.create_job() for _ in range(5)]
        first_job_id = job_ids[0]

        # Create 6th job, should evict the first one
        new_job_id = self.job_manager.create_job()

        self.assertIsNone(self.job_manager.get_job(first_job_id))
        self.assertIsNotNone(self.job_manager.get_job(new_job_id))

    def test_lru_behavior(self):
        job_ids = [self.job_manager.create_job() for _ in range(5)]
        # Access/Update first job to make it "recent"
        self.job_manager.update_job(job_ids[0], message="Touching first job")

        # Create 6th job, should evict the second job (which is now the oldest)
        self.job_manager.create_job()

        self.assertIsNotNone(self.job_manager.get_job(job_ids[0]))
        self.assertIsNone(self.job_manager.get_job(job_ids[1]))


if __name__ == "__main__":
    unittest.main()
