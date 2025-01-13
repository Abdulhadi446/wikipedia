from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from databases import Database
from sqlalchemy.orm import Session
import wikipedia
# uvicorn main:app --reload

# Set up the app and database
app = FastAPI()
Base = declarative_base()
DATABASE_URL = "sqlite:///./wiki.db"
database = Database(DATABASE_URL)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Define the Articles table
class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    content = Column(Text)

Base.metadata.create_all(bind=engine)

# Set up Jinja2 templates
templates = Environment(loader=FileSystemLoader("templates"))

# Static file serving (e.g., CSS, JavaScript)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_home():
    template = templates.get_template("home.html")
    return template.render()

@app.get("/all_articles", response_class=HTMLResponse)
async def all_articles_page(db: Session = Depends(get_db)):
    # Fetch all articles from the database
    articles = db.query(Article).all()
    
    # Render the 'all_articles.html' template and pass the articles to it
    template = templates.get_template("all_articles.html")
    return template.render(articles=articles)

@app.get("/article/{title}", response_class=HTMLResponse)
async def read_article(title: str, db: Session = Depends(get_db)):
    # Try to retrieve the article from the database
    article = db.query(Article).filter(Article.title == title).first()
    
    if not article:
        # If the article doesn't exist in the database, fetch it from Wikipedia
        try:
            content = wikipedia.summary(title)
            # Create a new Article object and add it to the database
            article = Article(title=title, content=content)
            db.add(article)
            db.commit()
        except wikipedia.exceptions.PageError:
            raise HTTPException(status_code=404, detail="Article not found")
        except wikipedia.exceptions.DisambiguationError as e:
            raise HTTPException(status_code=400, detail=f"Title is ambiguous. Options: {e.options}")
    
    # Render the article
    template = templates.get_template("article.html")
    return template.render(title=article.title, content=article.content)

@app.get("/create", response_class=HTMLResponse)
async def create_article_page():
    template = templates.get_template("create.html")
    return template.render()

@app.post("/create")
async def create_article(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    title = form_data.get("title")
    content = form_data.get("content")

    if not title or not content:
        raise HTTPException(status_code=400, detail="Title and content are required")

    new_article = Article(title=title, content=content)
    db.add(new_article)
    db.commit()
    return RedirectResponse(url=f"/article/{title}", status_code=303)

@app.get("/edit/{title}", response_class=HTMLResponse)
async def edit_article_page(title: str, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.title == title).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    template = templates.get_template("edit.html")
    return template.render(title=article.title, content=article.content)
    
@app.post("/edit/{title}")
async def edit_article(title: str, request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    new_content = form_data.get("content")

    article = db.query(Article).filter(Article.title == title).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.content = new_content
    db.commit()
    return RedirectResponse(url=f"/article/{title}", status_code=303)

@app.post("/delete/{title}")
async def delete_article(title: str, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.title == title).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(article)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

# Template files (e.g., home.html, article.html, create.html, edit.html) should be stored in the 'templates' directory.
# Static files (e.g., styles.css) should be stored in the 'static' directory.
# pip install fastapi uvicorn jinja2 sqlalchemy databases wikipedia