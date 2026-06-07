# Server Dashboard

Dashboard web en tiempo real con estadísticas del servidor: CPU, RAM, disco, red y procesos activos.

## Stack

- **Backend:** FastAPI + psutil
- **Frontend:** HTML / JS vanilla — single page
- **Deploy:** Dockerfile listo para Coolify / Docker / cualquier host

## Uso

### Docker

```bash
docker build -t server-dashboard .
docker run -p 8000:8000 server-dashboard
```

### Local

```bash
pip install -r requirements.txt
./start.sh
```

Visita `http://localhost:8000` para ver el dashboard.
