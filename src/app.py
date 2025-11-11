"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from . import models


app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


# Initialize DB and seed sample data if empty
models.init_db()
models.seed_initial_data()


def _activity_to_dict(a: models.Activity) -> dict:
    return {
        a.name: {
            "description": a.description,
            "schedule": a.schedule,
            "max_participants": a.max_participants,
            "participants": [p.email for p in a.participants],
        }
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    session = models.SessionLocal()
    try:
        activities = session.query(models.Activity).all()
        result = {}
        for a in activities:
            result.update(_activity_to_dict(a))
        return result
    finally:
        session.close()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    session = models.SessionLocal()
    try:
        activity = session.query(models.Activity).filter(models.Activity.name == activity_name).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # Validate student is not already signed up
        if any(p.email == email for p in activity.participants):
            raise HTTPException(status_code=400, detail="Student is already signed up")

        # Check capacity (0 means unlimited)
        if activity.max_participants and len(activity.participants) >= activity.max_participants:
            raise HTTPException(status_code=400, detail="Activity is full")

        participant = models.Participant(email=email, activity=activity)
        session.add(participant)
        session.commit()
        return {"message": f"Signed up {email} for {activity_name}"}
    finally:
        session.close()


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    session = models.SessionLocal()
    try:
        activity = session.query(models.Activity).filter(models.Activity.name == activity_name).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        participant = next((p for p in activity.participants if p.email == email), None)
        if not participant:
            raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

        session.delete(participant)
        session.commit()
        return {"message": f"Unregistered {email} from {activity_name}"}
    finally:
        session.close()
