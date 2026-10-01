from datetime import datetime, timezone, timedelta

from database import SessionLocal
from models import Job
from redis_client import redis_client


JOB_TIMEOUT = 60
MAX_RETRIES = 3


def recover_stuck_jobs():
    db = SessionLocal()

    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            seconds=JOB_TIMEOUT
        )

        stuck_jobs = (
            db.query(Job)
            .filter(
                Job.status == "PROCESSING",
                Job.started_at < cutoff_time
            )
            .all()
        )

        for job in stuck_jobs:
            print(f"Found stuck job: {job.id}")

            if job.attempts < MAX_RETRIES:
                job.status = "PENDING"
                job.error = "Worker failure detected. Retrying job."

                db.commit()

                redis_client.rpush("job_queue", job.id)

                print(
                    f"Job {job.id} requeued "
                    f"(attempt {job.attempts + 1})"
                )

            else:
                job.status = "FAILED"
                job.error = "Maximum retry attempts exceeded."

                db.commit()

                redis_client.rpush("dead_letter_queue", job.id)

                print(
                    f"Job {job.id} moved to dead letter queue"
                )

    finally:
        db.close()


if __name__ == "__main__":
    recover_stuck_jobs()