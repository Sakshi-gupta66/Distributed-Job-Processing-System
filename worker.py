from datetime import datetime, timezone

from database import SessionLocal
from models import Job
from redis_client import redis_client


MAX_RETRIES = 3


def process_job(job):
    if job.job_type == "addition":
        a = job.parameters.get("a")
        b = job.parameters.get("b")

        if a is None or b is None:
            raise ValueError("Parameters 'a' and 'b' are required")

        return {
            "result": a + b
        }

    raise ValueError(f"Unknown job type: {job.job_type}")


def worker():
    print("Worker started. Waiting for jobs...")

    while True:

        result = redis_client.blpop("job_queue", timeout=0)

        job_id = result[1]

        print(f"Received job: {job_id}")

        db = SessionLocal()

        try:
            job = db.get(Job, job_id)

            if job is None:
                print(f"Job {job_id} not found in database")
                continue

            job.status = "PROCESSING"
            job.started_at = datetime.now(timezone.utc)
            job.attempts += 1

            db.commit()

            print(
                f"Processing job: {job_id} "
                f"(attempt {job.attempts})"
            )

            output = process_job(job)

            job.status = "SUCCESS"
            job.result = output
            job.error = None
            job.completed_at = datetime.now(timezone.utc)

            db.commit()

            print(f"Job completed successfully: {job_id}")

        except Exception as e:

            print(f"Job failed: {job_id}")
            print(f"Error: {e}")

            if job.attempts < MAX_RETRIES:

                job.status = "PENDING"
                job.error = str(e)

                db.commit()

                redis_client.rpush("job_queue", job.id)

                print(
                    f"Job requeued: {job.id} "
                    f"(attempt {job.attempts + 1})"
                )

            else:

                job.status = "FAILED"
                job.error = (
                    f"Maximum retry attempts exceeded: {str(e)}"
                )
                job.completed_at = datetime.now(timezone.utc)

                db.commit()

                redis_client.rpush(
                    "dead_letter_queue",
                    job.id
                )

                print(
                    f"Job moved to DLQ: {job.id}"
                )

        finally:
            db.close()


if __name__ == "__main__":
    worker()