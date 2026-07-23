# Troubleshooting

Common issues when running the engine locally, especially on corporate networks or Windows.

## Port already in use

While the server is running, the terminal stays busy showing logs. That's normal. To stop the panel, press `Ctrl+C`.

If a socket error appears on Windows, the most common cause is a port already in use or blocked. Swap `8001` for another free port like `8501`:

```bash
python -m uvicorn api:app --reload --app-dir src --host 127.0.0.1 --port 8501
```

Check whether a port is busy:

```powershell
netstat -ano | Select-String ":8501"
```

Kill a stuck process (replace `<PID>` with the number shown):

```powershell
Stop-Process -Id <PID> -Force
```

## Corporate network / SSL issues

If your corporate network blocks SSL/HTTPS, try running with REST transport first:

```env
GEMINI_TRANSPORT=rest
```

The project also uses `truststore` to leverage Windows certificates automatically. After installing dependencies, restart the server.

If `CERTIFICATE_VERIFY_FAILED` or `self signed certificate` errors persist:

1. Test on another network to confirm the issue is the corporate proxy.
2. Ask IT for the corporate root certificate in `.pem` format.
3. Set `GEMINI_CA_BUNDLE` in `.env` pointing to that file:

```env
GEMINI_CA_BUNDLE=C:\path\to\corporate-cert.pem
```

Additional environment flags that help in restricted networks:

```env
GEMINI_USE_SYSTEM_CERTS=true
GEMINI_CHECK_DNS=false
```

## Model unavailable

`GEMINI_MODEL` uses the alias `gemini-flash-latest` by default. If the API returns that a model is unavailable for your key, the project tries the names listed in `GEMINI_FALLBACK_MODELS` before failing:

```env
GEMINI_FALLBACK_MODELS=gemini-3-flash-preview,gemini-pro-latest
```

You can override the primary model directly:

```env
GEMINI_MODEL=gemini-pro-latest
```
d