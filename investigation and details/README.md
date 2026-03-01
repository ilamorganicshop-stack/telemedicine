# Telemedicine

Django-based telemedicine project.

## Quick Start (Local)

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run migrations:

```bash
python manage.py migrate
```

4. Start the development server:

```bash
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`.

## Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

Environment variables:

- `DEBUG` (default `False`)
- `SECRET_KEY` (default `django-insecure-change-me-in-production`)
- `ALLOWED_HOSTS` (default `*`)

## Tests

```bash
python manage.py test
```
