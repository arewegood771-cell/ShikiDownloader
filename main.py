import flet as ft
from flet import Colors, Icons
import yt_dlp
import threading
import os


def main(page: ft.Page):
    page.title = "Nikisgi Downloader"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = "adaptive"  # Biar bisa di-scroll kalau layar HP kecil

    # --- LOGIC ---
    def on_download_click(e):
        url = url_input.value
        if not url:
            url_input.error_text = "Masukkin link dlu"
            page.update()
            return

        btn_download.disabled = True
        loading_ring.visible = True
        status_text.value = "Sabar cik, lagi diproses..."
        status_text.color = Colors.BLUE_200
        page.update()

        threading.Thread(target=process_download,
                         args=(url,), daemon=True).start()

    def process_download(url):
        # PENYESUAIAN UNTUK ANDROID: Simpan ke folder Download publik
        # Jika di Windows, ini akan tetap berfungsi (disimpan di folder Download user)
        if os.name == 'posix':  # Android/Linux
            download_path = "/sdcard/Download/%(title)s.%(ext)s"
        else:  # Windows
            download_path = "downloads/%(title)s.%(ext)s"

        fmt = format_dd.value
        res = res_dd.value
        fps = fps_dd.value

        if fmt == "mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': download_path,
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
            }
        else:
            ydl_opts = {
                'format': f'bestvideo[height<={res}][fps<={fps}]+bestaudio/best/best',
                'merge_output_format': fmt,
                'outtmpl': download_path,
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            status_text.value = "Done! Cek folder Download"
            status_text.color = Colors.GREEN_400
        except Exception as err:
            status_text.value = f"Error: {str(err)[:30]}..."
            status_text.color = Colors.RED_400

        loading_ring.visible = False
        btn_download.disabled = False
        page.update()

    # --- UI COMPONENTS ---
    url_input = ft.TextField(
        label="Link Video / Audio",
        border_radius=15,
        border_color=Colors.BLUE_400,
        width=400,
        prefix_icon=Icons.LINK
    )

    format_dd = ft.Dropdown(
        label="Format",
        width=110,
        options=[ft.dropdown.Option("mp4"), ft.dropdown.Option(
            "mkv"), ft.dropdown.Option("mp3")],
        value="mp4",
    )

    res_dd = ft.Dropdown(
        label="Res",
        width=110,
        options=[
            ft.dropdown.Option("2160", "4K"),
            ft.dropdown.Option("1080", "1080p"),
            ft.dropdown.Option("720", "720p"),
            ft.dropdown.Option("480", "480p")
        ],
        value="1080",
    )

    fps_dd = ft.Dropdown(
        label="FPS",
        width=110,
        options=[
            ft.dropdown.Option("60"),
            ft.dropdown.Option("50"),
            ft.dropdown.Option("30"),
            ft.dropdown.Option("24")
        ],
        value="60",
    )

    btn_download = ft.ElevatedButton(
        "Download Now",
        icon=Icons.DOWNLOAD_ROUNDED,
        on_click=on_download_click,
        width=250,
        height=50,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=Colors.BLUE_700,
            color=Colors.WHITE
        )
    )

    loading_ring = ft.ProgressRing(width=30, height=30, visible=False)
    status_text = ft.Text("", weight="bold", text_align="center")

    # --- LAYOUT ---
    main_container = ft.Container(
        content=ft.Column([
            ft.Icon(Icons.CLOUD_DOWNLOAD_OUTLINED,
                    size=60, color=Colors.BLUE_400),
            ft.Text("Nikisgi Downloader", size=28, weight="bold"),
            ft.Divider(height=10, color=Colors.TRANSPARENT),
            url_input,
            ft.Row([format_dd, res_dd, fps_dd], alignment="center", spacing=5),
            ft.Divider(height=20, color=Colors.TRANSPARENT),
            btn_download,
            loading_ring,
            status_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=25,
        bgcolor=Colors.GREY_900,
        border_radius=30,
    )

    page.add(main_container)


if __name__ == "__main__":
    ft.app(target=main)
