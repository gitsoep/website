# soep.org

The personal website behind [soep.org](https://soep.org): a small [FastAPI](https://fastapi.tiangolo.com/) app with a few network tools and some fun pages.

## Pages

| Path        | Description                                                                 |
|-------------|-----------------------------------------------------------------------------|
| `/`         | Shows your IPv4 and IPv6 address (click to copy). CLI clients get plain text. |
| `/whoami`   | Plain text: ASCII soup bowl, your IP, user agent and all request headers.   |
| `/headers`  | Your HTTP request headers as a page.                                         |
| `/random`   | UUID, password and dice generator (uses `crypto.getRandomValues`).           |
| `/terminal` | Fake shell: `help`, `ls`, `cat security.txt`, `whoami`, `sudo rm -rf /`… |
| `/matrix`   | Matrix digital rain animation.                                               |

### API

| Path                        | Description                         |
|-----------------------------|-------------------------------------|
| `/api/ip`                   | Your IP address as plain text.      |
| `/api/headers`              | Your request headers as JSON.       |
| `/health`                   | Health check, returns `ok`.         |
| `/robots.txt`               | For robots (with jokes).            |
| `/humans.txt`               | For humans (with jokes).            |
| `/.well-known/security.txt` | Security contact information.       |

### From the terminal

```sh
curl soep.org          # soup bowl + your IP
curl soep.org/whoami   # soup bowl + your IP + all headers
```

Requests from `curl`, `wget`, HTTPie and `xh` to `/` get plain text; browsers get the HTML page.

## Running locally

Requires Python 3.13.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open <http://localhost:8000>.

## Docker

```sh
docker build -t website .
docker run --rm -p 8000:8000 website
```

Or use the published image, see [docker-compose-example.yml](docker-compose-example.yml):

```sh
docker compose -f docker-compose-example.yml up -d
```

## Configuration

Set with environment variables (see [.env.example](.env.example)):

| Variable           | Default     | Description                                                           |
|--------------------|-------------|-----------------------------------------------------------------------|
| `ENABLE_ANALYTICS` | `false`     | Inject the OpenPanel analytics script (`1`/`true`/`yes`/`on`).        |
| `ANALYTICS_HTML`   | OpenPanel   | Custom analytics snippet. Setting this also enables analytics. `__CSP_NONCE__` is replaced with the request's CSP nonce. |
| `APP_VERSION`      | `0.1.4`     | Version shown in the footer.                                          |

## Security

Every response gets strict security headers, including a nonce-based Content Security Policy. Inline scripts and styles in templates must carry `nonce="{{ request.state.csp_nonce }}"`; inline `style=` attributes and `on*=` handlers are blocked.

## Project layout

```text
main.py                 FastAPI app, routes and security middleware
templates/              Jinja2 templates (all extend base.html)
static/                 Static files (analytics script, security.txt)
images/                 Favicon and avatar
Dockerfile              Production image (python:3.13-alpine, non-root)
.github/workflows/      Docker image build/push to GHCR and Trivy scan
```

## CI

Pushes to `main` build the image and push it to `ghcr.io/gitsoep/website` (tags `latest` and the commit SHA). Trivy scans the image on pushes, pull requests and weekly.
