from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import Job
from redis_client import redis_client


app = FastAPI(title="Distributed Job Processing Platform")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class JobRequest(BaseModel):
    job_type: str
    parameters: dict


class JobResponse(BaseModel):
    job_id: str
    status: str


@app.post("/jobs", response_model=JobResponse)
def create_job(
    job_request: JobRequest,
    db: Session = Depends(get_db)
):
    # 1. Create job in PostgreSQL
    job = Job(
        job_type=job_request.job_type,
        parameters=job_request.parameters,
        status="PENDING"
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # 2. Put job ID into Redis queue
    redis_client.rpush("job_queue", job.id)

    return JobResponse(
        job_id=job.id,
        status=job.status
    )


@app.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    job = db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "job_id": job.id,
        "job_type": job.job_type,
        "parameters": job.parameters,
        "status": job.status,
        "attempts": job.attempts,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }