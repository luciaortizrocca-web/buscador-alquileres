# 📊 Cómo conectar tu Planilla de Google Sheets (Acceso directo desde el Celular)

Si querés ver todas las propiedades encontradas directamente en la app de **Google Sheets** en tu celular, seguí estos 3 pasos simples:

---

### Paso 1: Crear la Planilla
1. Entrá a [Google Sheets](https://sheets.new) y creá una nueva planilla (ej: `Alquileres CABA`).
2. En la primera fila (encabezados), pegá estas columnas:
   - `Fecha` | `Portal` | `ID` | `Tipo` | `Barrio` | `Dirección` | `Alquiler` | `Expensas` | `Total` | `Ambientes` | `Superficie` | `Exterior` | `Título` | `Link` | `Estado`

---

### Paso 2: Agregar el Webhook (Apps Script)
1. En la planilla, hacé clic en el menú superior: **Extensiones** > **Apps Script**.
2. Borrá lo que haya y pegá este código:

```javascript
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  sheet.appendRow([
    data.fecha,
    data.portal,
    data.id,
    data.tipo,
    data.barrio,
    data.direccion,
    data.alquiler,
    data.expensas,
    data.total,
    data.ambientes,
    data.superficie,
    data.exterior,
    data.titulo,
    data.url,
    data.estado
  ]);
  return ContentService.createTextOutput("OK");
}
```

3. Hacé clic en **Implementar (Deploy)** > **Nueva implementación (New deployment)**.
4. Tipo: seleccioná **Aplicación web (Web app)**.
5. Configuración:
   - *Ejecutar como*: **Yo (tu cuenta)**.
   - *Quién tiene acceso*: **Cualquier usuario (Anyone)**.
6. Hacé clic en **Implementar** y copiá la **URL de la aplicación web**.

---

### Paso 3: Pegar la URL en config.json
Pegá la URL obtenida en tu `config.json` en el campo `"google_sheet_webhook_url"`:

```json
{
  "google_sheet_webhook_url": "https://script.google.com/macros/s/AKfycb.../exec"
}
```

¡Listo! A partir de ese momento, cada nuevo alquiler que encuentre el bot se agregará automáticamente como una nueva fila en tu Google Sheet en la nube, y lo vas a poder consultar y editar desde la app de tu celular.
