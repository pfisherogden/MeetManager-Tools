import unittest

from meetmanager.v1 import meet_manager_pb2 as pb2
from server import JobManager


class TestJobManager(unittest.TestCase):
    def setUp(self):
        self.job_manager = JobManager()

    def test_create_job(self):
        job_id = self.job_manager.create_job()
        self.assertIsNotNone(job_id)
        job = self.job_manager.get_job(job_id)
        self.assertIsNotNone(job)
        if job:
            self.assertEqual(job["status"], pb2.JOB_STATUS_PENDING)
            self.assertEqual(job["progress"], 0.0)

    def test_update_job(self):
        job_id = self.job_manager.create_job()
        self.job_manager.update_job(
            job_id, 
            status=pb2.JOB_STATUS_PROCESSING, 
            progress=0.5, 
            message="Halfway there"
        )
        job = self.job_manager.get_job(job_id)
        self.assertIsNotNone(job)
        if job:
            self.assertEqual(job["status"], pb2.JOB_STATUS_PROCESSING)
            self.assertEqual(job["progress"], 0.5)
            self.assertEqual(job["message"], "Halfway there")


    if __name__ == "__main__":
        unittest.main()

