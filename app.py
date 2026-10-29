"""
Dashboard Data Seniman Jawa Barat
Menggunakan Flask, pandas, dan Chart.js.

Cara menjalankan:
    python -m pip install -r requirements.txt
    python app.py

Buka browser:
    http://127.0.0.1:5000
"""

from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request


# ==================================================
# KONFIGURASI APLIKASI
# ==================================================

app = Flask(__name__)

# Mengambil lokasi folder proyek secara otomatis
BASE_DIR = Path(__file__).resolve().parent

# Lokasi file dataset
CSV_PATH = BASE_DIR / "data" / "seniman.csv"


# ==================================================
# MEMBACA DATASET
# ==================================================

try:
    df = pd.read_csv(CSV_PATH)

except FileNotFoundError:
    raise FileNotFoundError(
        f"File dataset tidak ditemukan: {CSV_PATH}\n"
        "Pastikan seniman.csv berada di folder data."
    )


# ==================================================
# VALIDASI KOLOM DATASET
# ==================================================

KOLOM_WAJIB = [
    "id",
    "kode_provinsi",
    "nama_provinsi",
    "kode_kabupaten_kota",
    "nama_kabupaten_kota",
    "jenis_kelamin",
    "jumlah_seniman",
    "satuan",
    "tahun",
]

kolom_hilang = [
    kolom
    for kolom in KOLOM_WAJIB
    if kolom not in df.columns
]

if kolom_hilang:
    raise ValueError(
        "Kolom berikut tidak ditemukan dalam seniman.csv: "
        + ", ".join(kolom_hilang)
    )


# ==================================================
# MEMBERSIHKAN DATA
# ==================================================

# Mengubah kolom angka ke tipe numerik
df["jumlah_seniman"] = pd.to_numeric(
    df["jumlah_seniman"],
    errors="coerce",
)

df["tahun"] = pd.to_numeric(
    df["tahun"],
    errors="coerce",
)

# Menghapus baris yang tidak memiliki informasi utama
df = df.dropna(
    subset=[
        "nama_kabupaten_kota",
        "jenis_kelamin",
        "jumlah_seniman",
        "tahun",
    ]
).copy()

# Menggunakan tipe integer untuk tahun
df["tahun"] = df["tahun"].astype(int)

# Membersihkan teks
kolom_teks = [
    "nama_provinsi",
    "nama_kabupaten_kota",
    "jenis_kelamin",
    "satuan",
]

for kolom in kolom_teks:
    df[kolom] = df[kolom].astype(str).str.strip()

# Memastikan nilai jumlah seniman tidak negatif
df = df[df["jumlah_seniman"] >= 0].copy()

if df.empty:
    raise ValueError(
        "Dataset seniman.csv tidak memiliki data valid."
    )


# ==================================================
# FUNGSI FILTER TAHUN
# ==================================================

def filter_data():
    """
    Mengambil data berdasarkan parameter tahun.

    Contoh:
        /api/ringkasan?tahun=2024

    Jika tahun tidak diberikan, semua tahun digunakan.
    """

    data = df

    tahun = request.args.get("tahun", default=None)

    if tahun is not None and tahun != "":
        try:
            tahun = int(tahun)
        except ValueError:
            raise ValueError(
                "Parameter tahun harus berupa angka."
            )

        data = data[data["tahun"] == tahun]

    return data


# ==================================================
# HALAMAN UTAMA DASHBOARD
# ==================================================

@app.route("/")
def dashboard():
    """
    Menampilkan halaman dashboard.html.
    """

    return render_template("dashboard.html")


# ==================================================
# API DAFTAR TAHUN
# ==================================================

@app.route("/api/tahun")
def daftar_tahun():
    """
    Mengembalikan daftar tahun yang tersedia.

    Contoh hasil:
        {
            "tahun": [2014, 2015, 2016, 2024]
        }
    """

    tahun = sorted(
        df["tahun"].unique().tolist()
    )

    return jsonify(
        tahun=[int(t) for t in tahun]
    )


# ==================================================
# API RINGKASAN DASHBOARD
# ==================================================

@app.route("/api/ringkasan")
def ringkasan():
    """
    Menghitung:
    - Total seniman
    - Jumlah kabupaten/kota
    - Tahun yang ditampilkan
    """

    data = filter_data()

    total_seniman = int(
        data["jumlah_seniman"].sum()
    )

    jumlah_kabupaten = int(
        data["nama_kabupaten_kota"].nunique()
    )

    tahun_pilihan = request.args.get(
        "tahun",
        default=None,
    )

    if tahun_pilihan:
        tahun_label = tahun_pilihan
    else:
        tahun_min = int(df["tahun"].min())
        tahun_max = int(df["tahun"].max())

        if tahun_min == tahun_max:
            tahun_label = str(tahun_min)
        else:
            tahun_label = f"{tahun_min}–{tahun_max}"

    return jsonify(
        total_seniman=total_seniman,
        jumlah_kabupaten=jumlah_kabupaten,
        tahun=tahun_label,
    )


# ==================================================
# API JUMLAH SENIMAN PER KABUPATEN/KOTA
# ==================================================

@app.route("/api/per-kabupaten")
def per_kabupaten():
    """
    Menghitung jumlah seniman per kabupaten/kota.

    Data dikelompokkan berdasarkan wilayah.
    Jika terdapat beberapa kategori jenis kelamin,
    jumlahnya dijumlahkan untuk setiap wilayah.
    """

    data = filter_data()

    hasil = (
        data.groupby("nama_kabupaten_kota")[
            "jumlah_seniman"
        ]
        .sum()
        .sort_values(ascending=False)
    )

    return jsonify(
        labels=hasil.index.tolist(),
        data=[
            int(nilai)
            for nilai in hasil.tolist()
        ],
    )


# ==================================================
# API JUMLAH SENIMAN BERDASARKAN JENIS KELAMIN
# ==================================================

@app.route("/api/jenis-kelamin")
def jenis_kelamin():
    """
    Menghitung jumlah seniman berdasarkan
    kategori jenis kelamin dalam dataset.
    """

    data = filter_data()

    hasil = (
        data.groupby("jenis_kelamin")[
            "jumlah_seniman"
        ]
        .sum()
        .sort_values(ascending=False)
    )

    return jsonify(
        labels=hasil.index.tolist(),
        data=[
            int(nilai)
            for nilai in hasil.tolist()
        ],
    )


# ==================================================
# API TREN JUMLAH SENIMAN PER TAHUN
# ==================================================

@app.route("/api/tren-tahun")
def tren_tahun():
    """
    Menampilkan tren jumlah seniman setiap tahun.

    Setiap jenis kelamin menjadi satu garis pada
    grafik agar perkembangannya bisa dibandingkan.
    Grafik ini menggunakan seluruh tahun dalam dataset,
    tanpa mengikuti filter tahun pada dashboard.
    """

    # Mengelompokkan jumlah seniman berdasarkan tahun
    # dan jenis kelamin.
    hasil = (
        df.groupby(
            ["tahun", "jenis_kelamin"]
        )["jumlah_seniman"]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )

    daftar_tahun = [
        int(tahun)
        for tahun in hasil.index.tolist()
    ]

    datasets = []

    for kategori in hasil.columns:
        datasets.append(
            {
                "label": str(kategori),
                "data": [
                    int(nilai)
                    for nilai in hasil[kategori].tolist()
                ],
            }
        )

    return jsonify(
        labels=daftar_tahun,
        datasets=datasets,
    )


# ==================================================
# PENANGANAN ERROR API
# ==================================================

@app.errorhandler(ValueError)
def tangani_value_error(error):
    """
    Mengembalikan pesan kesalahan dalam format JSON
    jika parameter filter tidak valid.
    """

    if request.path.startswith("/api/"):
        return jsonify(
            error=str(error)
        ), 400

    return str(error), 400


# ==================================================
# MENJALANKAN APLIKASI
# ==================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000,
    )