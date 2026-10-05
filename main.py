from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import Job
from redis_client import redis_client


Base.metadata.create_all(bind=engine)

app = FastAPI()


class JobRequest(BaseModel):
    job_type: str
    parameters: dict
    idempotency_key: str


class JobResponse(BaseModel):
    job_id: str
    status: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/jobs", response_model=JobResponse)
def create_job(
    job_request: JobRequest,
    db: Session = Depends(get_db)
):
    # Check whether this idempotency key was already used
    existing_job = (
        db.query(Job)
        .filter(Job.idempotency_key == job_request.idempotency_key)
        .first()
    )

    if existing_job:
        return JobResponse(
            job_id=existing_job.id,
            status=existing_job.status
        )

    # Create new job
    job = Job(
        job_type=job_request.job_type,
        parameters=job_request.parameters,
        idempotency_key=job_request.idempotency_key,
        status="PENDING"
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # Add job to Redis queue
    redis_client.rpush("job_queue", job.id)

    print(f"Job queued: {job.id}")

    return JobResponse(
        job_id=job.id,
        status=job.status
    )


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    job = db.get(Job, job_id)

    if job is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=job.id,
        status=job.status
    )