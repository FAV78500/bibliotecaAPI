from fastapi import FastAPI, HTTPException, status, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import List, Literal, Optional
from datetime import datetime

app = FastAPI(title="Biblioteca Digital API", description="API para el control de la Biblioteca Digital")

# Manejador global para devolver 400 en lugar de 422 en errores de validación de esquemas (Pydantic/FastAPI)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors(), "body": exc.body},
    )

class User(BaseModel):
    nombre: str = Field(..., min_length=1)
    correo: EmailStr

class BookCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    año: int = Field(..., gt=1450, le=datetime.now().year)
    paginas: int = Field(..., gt=1)

class Book(BookCreate):
    id: int
    estado: Literal["disponible", "prestado"] = "disponible"

class LoanCreate(BaseModel):
    book_id: int
    usuario: User

class LoanResponse(BaseModel):
    id: int
    book_id: int
    usuario: User

# --- Base de datos en memoria para propósitos de prueba ---
books_db: List[Book] = []
loans_db: List[LoanResponse] = []
book_id_counter = 1
loan_id_counter = 1

# --- Endpoints ---

# a. Registrar un libro
@app.post("/books/", response_model=Book, status_code=status.HTTP_201_CREATED)
def registrar_libro(book: BookCreate):
    global book_id_counter
    new_book = Book(id=book_id_counter, estado="disponible", **book.model_dump())
    books_db.append(new_book)
    book_id_counter += 1
    return new_book

# b. Listar todos los libros disponibles
@app.get("/books/disponibles", response_model=List[Book])
def listar_libros_disponibles():
    return [book for book in books_db if book.estado == "disponible"]

# c. Buscar un libro por su nombre
@app.get("/books/search", response_model=List[Book])
def buscar_libro(nombre: str):
    # Búsqueda parcial case-insensitive
    encontrados = [book for book in books_db if nombre.lower() in book.nombre.lower()]
    return encontrados

# d. Registrar el préstamo de un libro a un usuario
@app.post("/loans/", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
def registrar_prestamo(loan: LoanCreate):
    global loan_id_counter
    book = next((b for b in books_db if b.id == loan.book_id), None)
    
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Libro no encontrado")
    
    if book.estado == "prestado":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El libro ya esta prestado")
    
    # Marcar libro como prestado
    book.estado = "prestado"
    
    # Crear registro de prestamo
    new_loan = LoanResponse(id=loan_id_counter, book_id=loan.book_id, usuario=loan.usuario)
    loans_db.append(new_loan)
    loan_id_counter += 1
    return new_loan

# e. Marcar un libro como devuelto
@app.post("/loans/return/{book_id}", status_code=status.HTTP_200_OK)
def devolver_libro(book_id: int):
    # Buscar el prestamo activo correspondiente al libro
    loan = next((l for l in loans_db if l.book_id == book_id), None)
    
    if not loan:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El registro de prestamo ya no existe")
    
    # Marcar el libro como disponible
    book = next((b for b in books_db if b.id == book_id), None)
    if book:
        book.estado = "disponible"
        
    return {"mensaje": "Libro devuelto con exito"}

# f. Eliminar el registro de un prestamo
@app.delete("/loans/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_prestamo(loan_id: int):
    global loans_db
    loan = next((l for l in loans_db if l.id == loan_id), None)
    
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de prestamo no encontrado")
    
    # Eliminar el registro de prestamo de la lista base de datos
    loans_db = [l for l in loans_db if l.id != loan_id]
    
    return None
