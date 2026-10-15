# Llibreta D+ · Streamlit

Dashboard de trail running que lee tus actividades en directo de la API de intervals.icu.

## Probar en tu ordenador
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y pon tu API key
streamlit run app.py
```
Sin clave, puedes ver la app con datos ficticios: `DEMO=1 streamlit run app.py`.

## Publicar gratis en Streamlit Community Cloud
1. Sube esta carpeta a un repositorio de GitHub (el `.gitignore` evita subir `secrets.toml`).
2. Entra en https://share.streamlit.io → **Create app** → elige el repositorio, rama `main` y archivo `app.py`.
3. En **Advanced settings → Secrets** pega:
   ```toml
   ATHLETE_ID = "i608564"
   INTERVALS_API_KEY = "tu-api-key"
   APP_PASSWORD = "una-contraseña"   # opcional
   ```
4. Despliega. Después, en **Settings → Sharing**, deja la app como privada (solo tu email) o usa `APP_PASSWORD`.

La API key está en intervals.icu → Settings → Developer Settings.
