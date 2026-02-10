# PDF Report Generation Setup

KoNote can generate PDF reports for client progress and funder reports. This feature requires **WeasyPrint**, which has native library dependencies.

## Is PDF Required?

**No.** PDF generation is optional. The application works fully without it:
- All features except PDF export work normally
- Users can still view reports in their browser
- CSV export is available as an alternative
- Users can use browser "Print to PDF" functionality

## Quick Check

To verify if PDF generation is available, run:

```bash
python manage.py shell -c "from apps.reports.pdf_utils import is_pdf_available; print('PDF available:', is_pdf_available())"
```

## Installation by Platform

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

### Linux (Alpine — Docker)

```dockerfile
RUN apk add --no-cache \
    pango \
    gdk-pixbuf \
    fontconfig \
    ttf-freefont
```

### macOS

```bash
brew install pango gdk-pixbuf libffi
```

### Windows

Windows requires the GTK3 runtime libraries. There are two options:

**Option 1: MSYS2 (Recommended)**

1. Download and install [MSYS2](https://www.msys2.org/)
2. Open MSYS2 terminal and run:
   ```bash
   pacman -S mingw-w64-x86_64-pango mingw-w64-x86_64-gdk-pixbuf2
   ```
3. Add `C:\msys64\mingw64\bin` to your system PATH
4. Restart your terminal/IDE

**Option 2: GTK3 Installer**

1. Download the GTK3 runtime from the [GTK website](https://www.gtk.org/docs/installations/windows/)
2. Install and add the `bin` folder to your PATH
3. Restart your terminal/IDE

### Docker (Production)

The production Docker image should include these dependencies. Example Dockerfile snippet:

```dockerfile
FROM python:3.12-slim

# Install WeasyPrint dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ... rest of your Dockerfile
```

## Troubleshooting

### "cannot load library 'libgobject-2.0-0'"

The GTK libraries are not installed or not in PATH. See installation instructions above.

### "Fontconfig error: Cannot load default config file"

Install fontconfig and at least one font:

```bash
# Ubuntu/Debian
sudo apt install fontconfig fonts-liberation

# Alpine
apk add fontconfig ttf-freefont
```

### PDF generates but fonts look wrong

Install proper fonts:

```bash
# Ubuntu/Debian
sudo apt install fonts-liberation fonts-dejavu

# The application will use system fonts for PDF rendering
```

### Still not working?

1. Check the error message in the application (click "Technical details" on the error page)
2. Verify libraries are installed: `python -c "from weasyprint import HTML; print('OK')"`
3. Check WeasyPrint's official troubleshooting: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting

## Development Without PDF

If you're developing KoNote and don't need PDF functionality:

1. **The app runs fine without GTK** — all other features work
2. **PDF views show a helpful error page** — users aren't confused
3. **Tests skip PDF tests** if WeasyPrint isn't available

This is by design. You don't need to install GTK just to work on unrelated features.
