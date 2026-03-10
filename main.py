# Importación de FastAPI y sus componentes para manejar errores, estados HTTP y peticiones
from fastapi import FastAPI, HTTPException, status, Request
# Importación de la excepción de validación de FastAPI para capturar errores de formato en la petición
from fastapi.exceptions import RequestValidationError
# Importación de JSONResponse para retornar respuestas en formato JSON
from fastapi.responses import JSONResponse
# Importación de Pydantic para la creación de modelos de datos, validación y tipos específicos como EmailStr
from pydantic import BaseModel, Field, EmailStr, model_validator
# Importación de tipos de typing para definir listas, valores literales y opcionales
from typing import List, Literal, Optional
# Importación de datetime y date para obtener el año actual y para las validaciones de fechas
from datetime import datetime, date

# Creación de la instancia principal de la aplicación FastAPI con un título y descripción
app = FastAPI(title="Biblioteca Digital API", description="API para el control de la Biblioteca Digital")

# Manejador global para devolver 400 en lugar de 422 en errores de validación de esquemas (Pydantic/FastAPI)
# Este decorador captura cualquier excepción del tipo RequestValidationError en la aplicación
@app.exception_handler(RequestValidationError)
# Función asíncrona que se ejecuta cuando ocurre un error de validación
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Retorna una respuesta JSON personalizada
    return JSONResponse(
        # Establece el código de estado HTTP 400 (Bad Request)
        status_code=status.HTTP_400_BAD_REQUEST,
        # En el contenido se incluyen los detalles del error y el cuerpo de la petición que falló
        content={"detail": exc.errors(), "body": exc.body},
    )

# Modelo base para representar a un usuario de la biblioteca
class User(BaseModel):
    # Campo nombre de tipo cadena, obligatorio (con ...) y que debe tener al menos 1 carácter
    nombre: str = Field(..., min_length=1)
    # Campo correo que está validado automáticamente para ser un email válido
    correo: EmailStr

# Modelo para validar los datos al momento de crear un nuevo libro
class BookCreate(BaseModel):
    # El nombre del libro debe tener entre 2 y 100 caracteres
    nombre: str = Field(..., min_length=2, max_length=100)
    # El año de publicación debe ser mayor a 1450 y menor o igual al año actual
    año: int = Field(..., gt=1450, le=datetime.now().year)
    # El número de páginas debe ser mayor a 1
    paginas: int = Field(..., gt=1)

# Modelo completo de libro, que hereda los campos de BookCreate
class Book(BookCreate):
    # Identificador único del libro (generado por el sistema)
    id: int
    # Estado del libro, que solo puede tomar uno de dos valores y por defecto es "disponible"
    estado: Literal["disponible", "prestado"] = "disponible"

# Modelo para registrar un préstamo de un libro
class LoanCreate(BaseModel):
    # Identificador del libro que se desea prestar
    book_id: int
    # Información del usuario que realiza el préstamo
    usuario: User
    # Fecha en que se realiza el préstamo (por defecto la fecha actual)
    fecha_prestamo: date = Field(default_factory=date.today)
    # Fecha en que se espera el regreso del libro
    fecha_regreso: date

    # Validador de modelo para asegurar que la fecha de regreso es correcta
    @model_validator(mode='after')
    def check_dates(self) -> 'LoanCreate':
        if self.fecha_regreso < self.fecha_prestamo:
            raise ValueError('La fecha de regreso no puede ser anterior a la fecha de prestamo')
        return self

# Modelo de respuesta cuando se consulta o realiza un préstamo
class LoanResponse(BaseModel):
    # Identificador único del préstamo
    id: int
    # Identificador del libro prestado
    book_id: int
    # Información del usuario que tomó el libro prestado
    usuario: User
    # Fecha de emisión del préstamo
    fecha_prestamo: date
    # Fecha en la que el libro será retornado
    fecha_regreso: date

# --- Base de datos en memoria para propósitos de prueba ---
# Lista que almacena los libros registrados en el sistema
books_db: List[Book] = []
# Lista que almacena los préstamos registrados en el sistema
loans_db: List[LoanResponse] = []
# Contador para asignar IDs únicos de manera incremental a los libros
book_id_counter = 1
# Contador para asignar IDs únicos de manera incremental a los préstamos
loan_id_counter = 1

# --- Endpoints ---

# a. Registrar un libro
# Decorador que define un endpoint POST en la ruta /books/
# La respuesta se validará con el modelo Book y retornará el status HTTP 201 (Created)
@app.post("/books/", response_model=Book, status_code=status.HTTP_201_CREATED)
# Función para registrar un nuevo libro, recibe los datos validados por el modelo BookCreate
def registrar_libro(book: BookCreate):
    # Se indica que vamos a usar e incrementar la variable global del contador de libros
    global book_id_counter
    # Se crea una nueva instancia de Book inyectando el ID generado, el estado "disponible" y los datos recibidos
    new_book = Book(id=book_id_counter, estado="disponible", **book.model_dump())
    # Se añade el nuevo libro a la lista de base de datos en memoria
    books_db.append(new_book)
    # Se incrementa el contador de libros para el próximo registro
    book_id_counter += 1
    # Se retorna el libro recién creado
    return new_book

# b. Listar todos los libros disponibles
# Decorador que define un endpoint GET en la ruta /books/disponibles
# Retorna una lista de libros, validando con el modelo List[Book]
@app.get("/books/disponibles", response_model=List[Book])
# Función para devolver los libros que no están prestados
def listar_libros_disponibles():
    # Se filtra y retorna la lista listando únicamente los libros con estado "disponible"
    return [book for book in books_db if book.estado == "disponible"]

# c. Buscar un libro por su nombre
# Decorador que define un endpoint GET en la ruta /books/search
# Retorna una lista de libros que coincidan con la búsqueda
@app.get("/books/search", response_model=List[Book])
# Función que busca libros pasándole el parámetro 'nombre' (query string)
def buscar_libro(nombre: str):
    # Búsqueda parcial case-insensitive comparando la variable recibida contra los nombres registrados
    # Se convierte tanto el término de búsqueda como el nombre del libro a minúsculas para comparar
    encontrados = [book for book in books_db if nombre.lower() in book.nombre.lower()]
    # Se retorna la lista de libros encontrados
    return encontrados

# d. Registrar el préstamo de un libro a un usuario
# Decorador que define un endpoint POST en la ruta /loans/
# Retorna el registro de préstamo con status HTTP 201
@app.post("/loans/", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
# Función para registrar el préstamo, validando la petición con el modelo LoanCreate
def registrar_prestamo(loan: LoanCreate):
    # Se usa la variable global para el identificador único del préstamo
    global loan_id_counter
    # Se busca en la lista de libros si existe el ID especificado; si no lo encuentra, retorna None
    book = next((b for b in books_db if b.id == loan.book_id), None)
    
    # Si el libro no existe en la base de datos
    if not book:
        # Se lanza una excepción HTTP 404 de "No encontrado"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Libro no encontrado")
    
    # Si el libro existe, pero su estado ya es "prestado"
    if book.estado == "prestado":
        # Se lanza una excepción HTTP 409 de "Conflicto"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El libro ya esta prestado")
    
    # Marcar libro como prestado cambiando la propiedad estado del objeto
    book.estado = "prestado"
    
    # Crear registro de prestamo en base a los datos validados y el ID autogenerado
    new_loan = LoanResponse(
        id=loan_id_counter, 
        book_id=loan.book_id, 
        usuario=loan.usuario,
        fecha_prestamo=loan.fecha_prestamo,
        fecha_regreso=loan.fecha_regreso
    )
    # Se añade el préstamo a la lista en memoria
    loans_db.append(new_loan)
    # Se incrementa el contador de préstamos
    loan_id_counter += 1
    # Se retorna el registro del nuevo préstamo creado
    return new_loan

# e. Marcar un libro como devuelto
# Decorador que define un endpoint POST en la ruta /loans/return/{book_id}
# Retorna estatus HTTP 200 (OK) en caso exitoso
@app.post("/loans/return/{book_id}", status_code=status.HTTP_200_OK)
# Función para procesar la devolución que recibe como parámetro de ruta el identificador del libro
def devolver_libro(book_id: int):
    # Buscar el prestamo activo correspondiente al libro simulando una búsqueda en base de datos
    loan = next((l for l in loans_db if l.book_id == book_id), None)
    
    # Si no existe tal préstamo en los registros
    if not loan:
        # Se lanza una excepción HTTP 409 puesto que no se puede devolver un libro que no está prestado
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El registro de prestamo ya no existe")
    
    # Si se encontró el préstamo, debemos buscar el libro original para actualizar su estado
    book = next((b for b in books_db if b.id == book_id), None)
    # Si el libro existe (que debería existir)
    if book:
        # Se regresa el estado del libro a "disponible"
        book.estado = "disponible"
        
    # Se retorna un mensaje de confirmación en forma de diccionario JSON
    return {"mensaje": "Libro devuelto con exito"}

# f. Eliminar el registro de un prestamo
# Decorador que define un endpoint DELETE en la ruta /loans/{loan_id}
# Retorna status HTTP 204 (No Content) indicando que la operación de eliminación fue exitosa
@app.delete("/loans/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
# Función que procesa la eliminación a través de un ID de préstamo pasado en la ruta
def eliminar_prestamo(loan_id: int):
    # Indicamos que vamos a modificar la estructura de datos lista global loans_db
    global loans_db
    # Buscamos si existe la referencia del préstamo por eliminar
    loan = next((l for l in loans_db if l.id == loan_id), None)
    
    # Si no existe la referencia de ese préstamo
    if not loan:
        # Lanzamos HTTP 404 para indicar que no hay registro con ese ID
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de prestamo no encontrado")
    
    # Eliminar el registro de prestamo de la lista base de datos
    # Lo hace recreando la lista, incluyendo únicamente los préstamos que no coincidan con el ID a eliminar
    loans_db = [l for l in loans_db if l.id != loan_id]
    
    # Retorna None porque enviamos un 204 (sin contenido)
    return None
