import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_GPVfvUMTJ5L9@ep-shiny-cloud-a1hszzed-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    grade = Column(String, index=True)
    age = Column(Integer)
    guardian_name = Column(String)
    contact_number = Column(String)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    status = Column(String, default="active")
    enrollment_date = Column(String, nullable=True)

class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    author = Column(String)
    date = Column(String)
    priority = Column(String, default="medium")
    category = Column(String, default="updates")
    is_pinned = Column(Boolean, default=False)

class StockItem(Base):
    __tablename__ = "stock_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, default="other")
    quantity = Column(Integer)
    minimum_quantity = Column(Integer)
    unit = Column(String)
    description = Column(String, nullable=True)
    last_updated = Column(String, nullable=True)

class Donation(Base):
    __tablename__ = "donations"
    id = Column(Integer, primary_key=True, index=True)
    donor_name = Column(String)
    type = Column(String, default="monetary")
    amount = Column(Float)
    item_description = Column(String, nullable=True)
    status = Column(String, default="pending")
    date = Column(String)
    notes = Column(String, nullable=True)

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, index=True)
    grade = Column(String, index=True)
    date = Column(String, index=True)
    status = Column(String)

class SubjectGrade(Base):
    __tablename__ = "subject_grades"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, index=True)
    subject = Column(String)
    grade = Column(String)
    percentage = Column(Integer)
    credits = Column(Integer)
    teacher = Column(String)
    remarks = Column(String)
    term = Column(String)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    time = Column(String)
    icon = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hope Foundation API")

# CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_activity(db: Session, title: str, description: str, icon: str):
    import datetime
    new_log = ActivityLog(
        title=title,
        description=description,
        time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        icon=icon
    )
    db.add(new_log)
    db.commit()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return token

# --- Schemas ---
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str

class StudentRequest(BaseModel):
    name: str
    grade: str
    age: int
    guardianName: str
    contactNumber: str
    email: Optional[str] = None
    address: Optional[str] = None
    status: str = "active"

class AnnouncementRequest(BaseModel):
    title: str
    content: str
    author: str
    date: str
    priority: str = "medium"
    category: str = "updates"
    isPinned: bool = False

class StockItemRequest(BaseModel):
    name: str
    category: str = "other"
    quantity: int
    minimumQuantity: int
    unit: str
    description: Optional[str] = None

class DonationRequest(BaseModel):
    donorName: str
    type: str = "monetary"
    amount: float
    itemDescription: Optional[str] = None
    status: str = "pending"
    date: str
    notes: Optional[str] = None

class AttendanceRecord(BaseModel):
    id: str
    status: str

class SaveAttendanceRequest(BaseModel):
    grade: str
    date: str
    attendance: List[AttendanceRecord]

# --- Routes: Auth ---
@app.post("/api/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or user.password != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "name": user.name,
        "role": user.role,
        "token": f"mock_token_{user.role}"
    }

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        name=request.name,
        email=request.email,
        password=request.password,
        role=request.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "token": f"mock_token_{new_user.role}"
    }

# --- Routes: Dashboard ---
@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db), token: str = Depends(verify_token)):
    total_students = db.query(Student).count()
    stock_count = db.query(StockItem).count()
    donations = db.query(Donation).all()
    total_donations = sum(d.amount for d in donations)
    
    # Simple attendance rate calculation (if any records exist)
    all_attendance = db.query(Attendance).all()
    if all_attendance:
        present = len([a for a in all_attendance if a.status == "present"])
        rate = (present / len(all_attendance)) * 100
    else:
        rate = 0.0

    recent_activities = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(5).all()
    
    return {
        "totalStudents": {"title": "Total Students", "value": f"{total_students:,}", "change": 0.0, "icon": "people"},
        "attendanceRate": {"title": "Attendance Rate", "value": f"{rate:.1f}%", "change": 0.0, "icon": "check_circle"},
        "stockItems": {"title": "Stock Items", "value": str(stock_count), "change": 0.0, "icon": "inventory"},
        "totalDonations": {"title": "Total Donations", "value": f"${total_donations:,.0f}", "change": 0.0, "icon": "volunteer"},
        "recentActivities": [
            {
                "title": a.title,
                "description": a.description,
                "time": a.time,
                "icon": a.icon
            } for a in recent_activities
        ],
        "upcomingEvents": [
            {"title": "Annual Sports Day", "date": "2026-03-15", "time": "9:00 AM", "icon": "sports"},
            {"title": "Parent-Teacher Meeting", "date": "2026-03-20", "time": "2:00 PM", "icon": "meeting"}
        ],
        "impactItems": [
            {"title": "Quality Education", "icon": "education", "imageUrl": "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=300&fit=crop"},
            {"title": "Community Support", "icon": "community", "imageUrl": "https://images.unsplash.com/photo-1532629345422-7515f3d16bb6?w=400&h=300&fit=crop"}
        ]
    }

# --- Routes: Students ---
@app.get("/api/students")
def get_students(db: Session = Depends(get_db), token: str = Depends(verify_token)):
    students = db.query(Student).all()
    return {
        "students": [
            {
                "id": str(s.id), "name": s.name, "grade": s.grade, "age": s.age,
                "guardianName": s.guardian_name, "contactNumber": s.contact_number,
                "email": s.email, "address": s.address,
                "status": s.status, "enrollmentDate": s.enrollment_date
            } for s in students
        ]
    }

@app.post("/api/students", status_code=status.HTTP_201_CREATED)
def add_student(request: StudentRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    new_student = Student(
        name=request.name,
        grade=request.grade,
        age=request.age,
        guardian_name=request.guardianName,
        contact_number=request.contactNumber,
        email=request.email,
        address=request.address,
        status=request.status,
        enrollment_date="2026-03-28" # Current date shim
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    
    log_activity(db, "New Student Enrolled", f"{new_student.name} was added to {new_student.grade}", "person_add")
    
    return {"success": True, "student": request.model_dump()}

@app.get("/api/student/{student_id}")
def get_student_profile(student_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {
        "id": str(student.id), "name": student.name, "grade": student.grade, "age": student.age,
        "guardianName": student.guardian_name, "contactNumber": student.contact_number,
        "status": student.status, "enrollmentDate": student.enrollment_date
    }

@app.put("/api/students/{student_id}")
def update_student(student_id: int, request: StudentRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student.name = request.name
    student.grade = request.grade
    student.age = request.age
    student.guardian_name = request.guardianName
    student.contact_number = request.contactNumber
    student.email = request.email
    student.address = request.address
    student.status = request.status
    
    db.commit()
    return {"success": True, "student": request.model_dump()}

@app.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return {"success": True, "message": "Student deleted successfully"}

@app.get("/api/student/{student_id}/grades")
def get_student_grades(student_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    grades = db.query(SubjectGrade).filter(SubjectGrade.student_id == student_id).all()
    if not grades:
        return {"overallGpa": 0, "performanceLevel": "N/A", "subjects": [], "terms": [], "finalAverage": 0}
    
    subjects = [
        {
            "id": str(g.id), "subject": g.subject, "grade": g.grade, 
            "percentage": g.percentage, "credits": g.credits, 
            "teacher": g.teacher, "remarks": g.remarks
        } for g in grades
    ]
    
    avg_pct = sum(g.percentage for g in grades) / len(grades)
    
    return {
        "overallGpa": round(avg_pct / 10, 2),
        "performanceLevel": "Excellent" if avg_pct > 90 else "Good" if avg_pct > 75 else "Satisfactory",
        "subjects": subjects,
        "terms": [{"term": "Term 1", "percentage": int(avg_pct), "grade": "A"}], # Simplified
        "finalAverage": int(avg_pct)
    }

# --- Routes: Attendance ---
@app.get("/api/attendance")
def get_attendance(grade: str, date: str, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    records = db.query(Attendance).filter(Attendance.grade == grade, Attendance.date == date).all()
    # Join with students to get names
    students = db.query(Student).filter(Student.grade == grade).all()
    
    attendance_data = []
    summary = {"totalStudents": len(students), "present": 0, "absent": 0, "late": 0}
    
    records_map = {r.student_id: r.status for r in records}
    
    for s in students:
        status = records_map.get(s.id, "absent") # Default to absent if no record
        attendance_data.append({
            "id": str(s.id), "name": s.name, "grade": s.grade, "age": s.age, "status": status
        })
        if status in summary:
            summary[status] += 1
            
    return {"students": attendance_data, "summary": summary}

@app.post("/api/attendance/save")
def save_attendance(request: SaveAttendanceRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    # Deleting old records for the same day/grade to avoid duplicates
    db.query(Attendance).filter(Attendance.grade == request.grade, Attendance.date == request.date).delete()
    
    for record in request.attendance:
        new_record = Attendance(
            student_id=int(record.id),
            grade=request.grade,
            date=request.date,
            status=record.status
        )
        db.add(new_record)
    
    db.commit()
    return {"success": True, "message": "Attendance saved successfully"}

# --- Routes: Announcements ---
@app.get("/api/announcements")
def get_announcements(db: Session = Depends(get_db), token: str = Depends(verify_token)):
    announcements = db.query(Announcement).order_by(Announcement.is_pinned.desc(), Announcement.date.desc()).all()
    return {
        "announcements": [
            {
                "id": str(a.id), "title": a.title, "content": a.content,
                "author": a.author, "date": a.date, "priority": a.priority,
                "category": a.category, "isPinned": a.is_pinned
            } for a in announcements
        ]
    }

@app.post("/api/announcements", status_code=status.HTTP_201_CREATED)
def add_announcement(request: AnnouncementRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    new_announcement = Announcement(
        title=request.title,
        content=request.content,
        author=request.author,
        date=request.date,
        priority=request.priority,
        category=request.category,
        is_pinned=request.isPinned
    )
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    return {"success": True, "announcement": request.model_dump()}

@app.put("/api/announcements/{announcement_id}")
def update_announcement(announcement_id: int, request: AnnouncementRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    announcement.title = request.title
    announcement.content = request.content
    announcement.author = request.author
    announcement.date = request.date
    announcement.priority = request.priority
    announcement.category = request.category
    announcement.is_pinned = request.isPinned
    
    db.commit()
    return {"success": True, "announcement": request.model_dump()}

@app.delete("/api/announcements/{announcement_id}")
def delete_announcement(announcement_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    db.delete(announcement)
    db.commit()
    return {"success": True, "message": "Announcement deleted successfully"}

# --- Routes: Stock ---
@app.get("/api/stock")
def get_stock(db: Session = Depends(get_db), token: str = Depends(verify_token)):
    items = db.query(StockItem).all()
    categories = set(i.category for i in items)
    low_stock = [i for i in items if i.quantity <= i.minimum_quantity]
    
    return {
        "items": [
            {
                "id": str(i.id), "name": i.name, "category": i.category,
                "quantity": i.quantity, "minimumQuantity": i.minimum_quantity, 
                "unit": i.unit, "lastUpdated": i.last_updated
            } for i in items
        ],
        "summary": {
            "totalItems": len(items), 
            "categories": len(categories), 
            "lowStockItems": len(low_stock), 
            "outOfStockItems": len([i for i in items if i.quantity == 0])
        }
    }

@app.post("/api/stock", status_code=status.HTTP_201_CREATED)
def add_stock_item(request: StockItemRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    new_item = StockItem(
        name=request.name,
        category=request.category,
        quantity=request.quantity,
        minimum_quantity=request.minimumQuantity,
        unit=request.unit,
        description=request.description,
        last_updated="2026-03-28"
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    log_activity(db, "Stock Item Added", f"{new_item.name} ({new_item.quantity} {new_item.unit}) added to inventory", "inventory")
    
    return {"success": True, "item": request.model_dump()}

@app.put("/api/stock/{item_id}")
def update_stock_item(item_id: int, request: StockItemRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    item = db.query(StockItem).filter(StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    item.name = request.name
    item.category = request.category
    item.quantity = request.quantity
    item.minimum_quantity = request.minimumQuantity
    item.unit = request.unit
    item.description = request.description
    item.last_updated = "2026-03-28"
    
    db.commit()
    return {"success": True, "item": request.model_dump()}

@app.delete("/api/stock/{item_id}")
def delete_stock_item(item_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    item = db.query(StockItem).filter(StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    db.delete(item)
    db.commit()
    return {"success": True, "message": "Stock item deleted successfully"}

# --- Routes: Donations ---
@app.get("/api/donations")
def get_donations(db: Session = Depends(get_db), token: str = Depends(verify_token)):
    donations = db.query(Donation).all()
    total_amount = sum(d.amount for d in donations)
    
    return {
        "donations": [
            {
                "id": str(d.id), "donorName": d.donor_name, "type": d.type,
                "amount": d.amount, "status": d.status, "date": d.date
            } for d in donations
        ],
        "summary": {
            "totalDonations": total_amount, 
            "totalDonors": len(set(d.donor_name for d in donations)),
            "monthlyDonations": total_amount, # Simplified
            "percentageChange": 0.0
        }
    }

@app.post("/api/donations", status_code=status.HTTP_201_CREATED)
def add_donation(request: DonationRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    new_donation = Donation(
        donor_name=request.donorName,
        type=request.type,
        amount=request.amount,
        item_description=request.itemDescription,
        status=request.status,
        date=request.date,
        notes=request.notes
    )
    db.add(new_donation)
    db.commit()
    db.refresh(new_donation)
    
    log_activity(db, "New Donation Received", f"${new_donation.amount:,.0f} from {new_donation.donor_name}", "volunteer_activism")
    
    return {"success": True, "donation": request.model_dump()}

@app.put("/api/donations/{donation_id}")
def update_donation(donation_id: int, request: DonationRequest, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    
    donation.donor_name = request.donorName
    donation.type = request.type
    donation.amount = request.amount
    donation.item_description = request.itemDescription
    donation.status = request.status
    donation.date = request.date
    donation.notes = request.notes
    
    db.commit()
    return {"success": True, "donation": request.model_dump()}

# --- Routes: Teacher ---
@app.get("/api/teacher/dashboard")
def get_teacher_dashboard(db: Session = Depends(get_db), token: str = Depends(verify_token)):
    # Assuming we might filter by teacher's grade in a real scenario
    students = db.query(Student).all()
    announcements = db.query(Announcement).limit(5).all()
    
    return {
        "students": [
            {
                "id": str(s.id), "name": s.name, "grade": s.grade, "age": s.age,
                "guardianName": s.guardian_name, "contactNumber": s.contact_number,
                "status": s.status, "enrollmentDate": s.enrollment_date
            } for s in students
        ],
        "announcements": [
            {
                "id": str(a.id), "title": a.title, "content": a.content,
                "author": a.author, "date": a.date, "priority": a.priority, 
                "category": a.category, "isPinned": a.is_pinned
            } for a in announcements
        ]
    }

# --- Routes: Student Dashboard ---
@app.get("/api/student/{student_id}/dashboard")
def get_student_dashboard(student_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    announcements = db.query(Announcement).filter(Announcement.category.in_(["events", "academic"])).limit(5).all()
    attendance = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    
    present = len([a for a in attendance if a.status == "present"])
    absent = len([a for a in attendance if a.status == "absent"])
    late = len([a for a in attendance if a.status == "late"])
    total = len(attendance)
    rate = (present / total * 100) if total > 0 else 0.0

    return {
        "profile": {
            "id": str(student.id), "name": student.name, "grade": student.grade, "age": student.age,
            "guardianName": student.guardian_name, "contactNumber": student.contact_number,
            "status": student.status, "enrollmentDate": student.enrollment_date
        },
        "announcements": [
            {
                "id": str(a.id), "title": a.title, "content": a.content,
                "author": a.author, "date": a.date, "priority": a.priority, 
                "category": a.category, "isPinned": a.is_pinned
            } for a in announcements
        ],
        "attendance": {
            "present": present, "absent": absent, "late": late,
            "totalDays": total, "attendanceRate": round(rate, 1)
        }
    }

if __name__ == "__main__":
    # PORT is automatically provided by Render; default to 8080 for local dev.
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
