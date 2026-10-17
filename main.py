from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from database import create_tables, get_connection
from schemas import TodoCreate, TodoUpdate, TodoResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Todo API",
    description="A simple Todo API using FastAPI and SQLite",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {"message": "Welcome to the Todo API"}

@app.get("/todos",
         response_model=list[TodoResponse],
         status_code=status.HTTP_200_OK)
def get_todos():
    with get_connection() as connection:
        rows = connection.execute(
        "SELECT * FROM todos ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/todos/{todo_id}",
         response_model=TodoResponse,
         status_code=status.HTTP_200_OK)
def get_todo(todo_id:int):
    with get_connection() as connection:
        row = connection.execute(
        "SELECT * FROM todos WHERE id = ?"
        ,(todo_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Todo not Found"
            )
    return dict(row)

@app.post(
    "/todos",
    response_model=TodoResponse,
)
def create_todo(todo: TodoCreate):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO todos (title, description)
            VALUES (?, ?)
            """,
            (todo.title, todo.description),
        )

        row = connection.execute(
            "SELECT * FROM todos WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return dict(row)

@app.patch("/todos/{todo_id}",
         response_model=TodoResponse,
)
def update_todo(todo_id:int, todo:TodoUpdate):
    updates = todo.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT * FROM todos WHERE id = ?",
            (todo_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Todo not found",
            )
        columns = {
            "title": "title",
            "description": "description",
            "completed": "completed",
        }

        set_clause = ", ".join(
            f"{columns[field]} = ?" for field in updates
        )
        values = [
                int(value) if field == "completed" and value is not None else value
                for field, value in updates.items()
            ]
        connection.execute(
            f'UPDATE todos SET {set_clause} WHERE id = ?',
            (*values,todo_id),
        )
        row = connection.execute(
            "SELECT * FROM todos WHERE id = ?",
            (todo_id,)
        ).fetchone()
        return dict(row)