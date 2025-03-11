import tkinter as tk
from tkinter import messagebox
import threading
import cv2
from pytube import YouTube
import os

# variabel global untuk menyimpan objek youtube dan daftar stream yang tersedia
yt_obj = None
streams_available = {}

def log_message(message):
    """
    Fungsi untuk menampilkan log pesan di area teks.
    """
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)
    
def fetch_video_info():
    """
    Fungsi untuk mengambil info video dari URL youtube yang diinput.
    Menampilkan daftar resolusi yang tersedia di dropdown.
    """
    global yt_obj, streams_available
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Masukkan URL YouTube!")
        return
    log_message("Mengambil info video...")
    try:
        yt_obj = YouTube(url)
        # Ambil stream yang bersifat progressive (video+audio) dan berformat mp4
        streams = yt_obj.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
        streams_available = {}
        options = []
        for s in streams:
            res = s.resolution
            if res not in streams_available:
                streams_available[res] = s
                options.append(res)
        if options:
            resolution_var.set(options[0])
            resolution_menu['menu'].delete(0, 'end')
            for option in options:
                resolution_menu['menu'].add_command(label=option, command=tk._setit(resolution_var, option))
            log_message("Info video berhasil diambil!")
            log_message(f"Judul: {yt_obj.title}")
        else:
            log_message("Tidak ada stream yang sesuai ditemukan!")
    except Exception as e:
        log_message(f"Error mengambil info video: {str(e)}")
        messagebox.showerror("Error", f"Gagal mengambil info video: {str(e)}")
        
def download_and_capture():
    """
    Fungsi utama untuk:
    - Mengunduh video dengan resolusi yang dipilih
    - Mengambil beberapa frame berdasarkan timestamp yang diinput
    - Melakukan crop (jika parameter crop diisi)
    Penanganan error dilakukan di setiap langkah
    """
    def process():
        url = url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Masukkan URL YouTube!")
            return
        if yt_obj is None:
            messagebox.showerror("Error", "Info video belum diambil. Klik 'Fetch Video Info' terlebih dahulu!")
            return
        stream = streams_available[selected_res]
        video_filename = "download_video.mp4"
        log_message("Mengunduh video...")
        try:
            stream.download(filename=video_filename)
            log_message("Video berhasil diunduh!")
        except Exception as e:
            log_message(f"Error mengunduh video: {str(e)}")
            messagebox.showerror("Error", f"Gagal mengunduh video: {str(e)}")
            return
        
        # Mengambil beberapa timestamp (dipisahkan dengan koma)
        timestamps_str = timestamps_entry.get().strip()
        if not timestamps_str:
            messagebox.showerror("Error", "Masukkan minimal satu timestamp!")
            return
        try:
            # Misal: "5,10,15" akan menjadi [5.0, 10.0, 15.0]
            timestamps = [float(ts.strip()) for ts in timestamps_str.split(",") if ts.strip() != ""]
        except Exception as e:
            log_message(f"Error parsing timestamps: {str(e)}")
            messagebox.showerror("Error", "Format timestamp salah. Gunakan koma sebagai pemisah, misal: 5,10,15")
            return
        
        # Parsing parameter crop (opsional)
        crop_params_str = crop_entry.get().strip()
        crop_params = None
        if crop_params_str:
            try:
                parts = [int(x.strip()) for x in crop_params_str.split(",")]
                if len(parts) != 4:
                    raise ValueError("Harus ada 4 nilai: x, y, width, height")
                crop_params = parts # [x, y, width, height]
            except Exception as e:
                log_message(f"Error parsing crop parameters: {str(e)}")
                messagebox.showerror("Error", "Format crop salah. Gunakan: x, y, width, height (misal: 100,50,300,200)")
                return
            
        # Buka video dengan OpenCV
        cap = cv2.VideoCapture(video_filename)
        if not cap.isOpened():
            log_message("Error membuka video!")
            messagebox.showerror("Error", "Gagal membuka video yang diunduh!")
            return
        
        frame_count = 0
        for ts in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
            ret, frame = cap.read()
            if ret:
                # Jika parameter crop sudah diinput, lakukan crop frame
                if crop_params:
                    x, y, w, h = crop_params
                    # validasi agar crop tidak melebihi batas dimensi frame
                    if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
                        log_message(f"Crop parameters melebihi batas frame pada timestamp {ts} detik. Frame tidak dipotong.")
                    else:
                        frame = frame[y:y+h, x:x+w]
                frame_filename = f"frame_{frame_count+1}_at_{ts:.2f}s.jpg"
                cv2.imwrite(frame_filename, frame)
                log_message(f"Frame pada {ts} detik disimpan sebagai {frame_filename}")
                frame_count += 1
            else:
                log_message(f"Gagal mengambil frame pada {ts} detik.")
        cap.release()
        
        # Hapus file video yang sudah diunduh agar tidak memenuhi ruang disk
        if os.path.exists(video_filename):
            os.remove(video_filename)
            log_message("Video yang diunduh telah dihapus.")
            
        log_message("Proses pengambilan frame selesai.")
        
    # Jalankan fungsi process di thread terpisah agar GUI tidak freeze
    threading.Thread(target=process).start()
    
# ====================
# Pembuatan GUI dengan Tkinter
# ====================

root = tk.Tk()
root.title("YouTube video frame capture")
root.geometry("600x400")

# Frame untuk input
input_frame = tk.Frame(root)
input_frame.pack(pady=10, padx=10, fill=tk.X)

# Input URL YouTube
tk.Label(input_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W)
url_entry = tk.Entry(input_frame, width=50)
url_entry.grid(row=0, column=1, padx=5, pady=5)

# Tombol untuk mengambil info video
fetch_button = tk.Button(input_frame, text="Fetch Video Info", command=fetch_video_info)
fetch_button.grid(row=0, column=2, padx=5, pady=5)

# Dropdown pilihan resolusi video
tk.Label(input_frame, text="Pilih Resolusi:").grid(row=1, column=0, sticky=tk.W)
resolution_var = tk.StringVar()
resolution_menu = tk.OptionMenu(input_frame, resolution_var, "")
resolution_menu.config(width=10)
resolution_menu.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

# Input timestamp untuk pengambilan frame
tk.Label(input_frame, text="Timestamps (detik, pisahkan dengan koma):").grid(row=2, column=0, sticky=tk.W)
timestamps_entry = tk.Entry(input_frame, width=50)
timestamps_entry.grid(row=2, column=1, padx=5, pady=5)

# Input parameter crop (opsional)
tk.Label(input_frame, text="Crop coordinates (x,y,width,height) - Opsional:").grid(row=3, column=0, sticky=tk.W)
crop_entry = tk.Entry(input_frame, width=50)
crop_entry.grid(row=3, column=1, padx=5, pady=5)

# Tombol untuk memulai proses unduh & capture frame
download_button = tk.Button(root, text="Download dan Capture Frame", command=download_and_capture)
download_button.pack(pady=10)

# Area log untuk menampilkan pesan proses
log_text = tk.Text(root, height=10)
log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

root.mainloop()