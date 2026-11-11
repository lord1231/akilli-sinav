from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import ParentStudentLink, User
from app.schemas import CreateStudent, LoginRequest, RegisterParent, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Kimlik doğrulama"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_parent(payload: RegisterParent, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı.")
    user = User(email=email, password_hash=hash_password(payload.password),
                full_name=payload.full_name.strip(), role="parent")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-posta veya parola hatalı.")
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/students", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: CreateStudent, parent: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if parent.role != "parent":
        raise HTTPException(status_code=403, detail="Öğrenci hesabını yalnızca veli oluşturabilir.")
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı.")
    student = User(email=email, password_hash=hash_password(payload.password),
                   full_name=payload.full_name.strip(), role="student",
                   grade_level=payload.grade_level)
    db.add(student)
    db.flush()
    db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, consent_confirmed=True))
    db.commit()
    db.refresh(student)
    return student


@router.get("/students", response_model=list[UserResponse])
def list_my_students(parent: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if parent.role != "parent":
        raise HTTPException(status_code=403, detail="Yalnızca veliler erişebilir.")
    return list(db.scalars(select(User).join(ParentStudentLink, ParentStudentLink.student_id == User.id)
                            .where(ParentStudentLink.parent_id == parent.id)).all())
