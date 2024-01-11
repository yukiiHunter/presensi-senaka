import streamlit as st
from streamlit_drawable_canvas import st_canvas
from supabase import Client
import io
from PIL import Image
from datetime import datetime
import requests
from geopy.distance import geodesic
from streamlit_geolocation import streamlit_geolocation
import streamlit.components.v1 as components
import pandas as pd

# Set your Supabase project URL and API key
supabase_url = "https://hmnsudaftcyngykefncr.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhtbnN1ZGFmdGN5bmd5a2VmbmNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDQ4ODA4NTcsImV4cCI6MjAyMDQ1Njg1N30.gfxRwUGG8Lb8G4YTsAfZCa0PLv2dc4SRsyD6RZhng1M"

# Connect to Supabase
client = Client(supabase_url, supabase_key)

query_params = st.experimental_get_query_params()

def main():
    st.title("Form Presensi")
    
    # if "admin" in query_params and query_params["admin"][0] == "True":
    #     webbrowser.open("https://admin-senaka.streamlit.app/")        
        
    nama = st.text_input("Nama")
    kelas = st.text_input("Kelas")
    
    # Validating input
    if not nama or not kelas:
        st.warning("Nama dan kelas harus diisi.")
        return
    
    tanggal_presensi = datetime.today().date()
    st.write(f"Tanggal Presensi: {tanggal_presensi.strftime('%Y-%m-%d')}")

    st.write("Tanda Tangan:")
    signature = st_canvas(
        width=400,
        height=200,
        drawing_mode="freedraw",
        background_color="white",
        stroke_width=2,
        display_toolbar=True
    )
    
    st.write("Aktifkan GPS:")
    # Get user's location
    location = streamlit_geolocation()
    if location and 'latitude' in location and 'longitude' in location:
        st.write(f"Latitude: {location['latitude']}, Longitude: {location['longitude']}")
    else:
        st.warning("User location not available.")

    # Check if the user is within a specified distance from the reference location
    allowed_distance = 100.0

    if st.button("Submit"):
        if is_within_distance(location, allowed_distance):

            # Convert canvas result to image
            signature_image = Image.fromarray(signature.image_data.astype('uint8'))

            # Convert RGBA to RGB
            signature_image = signature_image.convert("RGB")

            # Save the image to a BytesIO object
            signature_bytes = io.BytesIO()
            signature_image.save(signature_bytes, format='PNG')  # Save as PNG for transparency support

            # Save the image to the signature folder with a filename based on nama and tanggal_presensi
            filename = f"signature/{nama}_{tanggal_presensi}.png"

            # Upload the image using requests
            files = {'file': (filename, signature_bytes.getvalue(), 'image/png')}
            response = requests.post(f'{supabase_url}/storage/v1/object/{filename}', files=files, headers={'Authorization': f'Bearer {supabase_key}'})

            # Check if the upload was successful
            if response.status_code == 200:
                st.success("Presensi berhasil di-submit!")
                storage_url = f"{supabase_url}/storage/v1/object/public/{filename}"

                # Prepare data for insertion
                presensi_data = {
                    'nama': nama,
                    'kelas': kelas,
                    'tanggal': str(tanggal_presensi),
                    'foto': storage_url,
                }

               
                # Check if the record already exists
                response = client.table('presensi').select().eq('nama', nama).execute()
                existing_record = response.data if hasattr(response, 'data') else []

                if existing_record:
                    # Update existing record
                    presensi_response, presensi_error = client.table('presensi').upsert([presensi_data], on_conflict=['nama']).execute()
                else:
                    # Insert new record
                    presensi_response, presensi_error = client.table('presensi').insert([presensi_data]).execute()


                # Display input details and signature image
                st.write("### Input Details:")
                st.write(f"Nama: {nama}")
                st.write(f"Kelas: {kelas}")
                st.write(f"Tanggal Presensi: {tanggal_presensi}")

                st.write("### Signature:")
                st.image(signature_bytes, caption='Tanda Tangan', use_column_width=True)

            else:
                st.error(f"Kamu sudah presensi hari ini")
        else:
            st.error("Presensi gagal di-submit. Anda berada di lokasi yang tidak diizinkan.")


def is_within_distance(user_location, allowed_distance):
    if user_location and 'latitude' in user_location and 'longitude' in user_location:
        user_point = (user_location['latitude'], user_location['longitude'])
        
        # Specify the reference location (latitude, longitude)
        reference_location = (-6.9858542, 110.4150302)

        # Calculate the distance between user's location and the reference location
        distance = geodesic(reference_location, user_point).miles

        # Print the calculated distance for debugging
        st.write(f"Distance: {distance} m")

        # Check if the distance is within the allowed range
        return distance <= allowed_distance

    return False


def admin():
    # Input kode
    kode_input = st.text_input("Masukkan kode admin:", type="password")

    # Cek jika kode benar
    if kode_input == "SenakaNewGen":
        st.write("Halo admin")

        # Ambil data dari tabel presensi
        response = client.table('presensi').select('nama', 'kelas', 'tanggal', 'foto').execute()
        presensi_data = response.data if hasattr(response, 'data') else []

        # Tampilkan data dalam bentuk tabel
        st.write("### Data Presensi:")
        if presensi_data:
            # Buat DataFrame dari data presensi
            df_presensi = pd.DataFrame(presensi_data)

            # Convert 'tanggal' column to datetime
            df_presensi['tanggal'] = pd.to_datetime(df_presensi['tanggal'])

            # Tambahkan kolom baru dengan HTML untuk menampilkan gambar
            df_presensi['image'] = df_presensi['foto'].apply(lambda url: f'<img src="{url}" width="300">')

            # Hapus kolom foto (jika tidak ingin menampilkannya)
            df_presensi = df_presensi.drop(columns=['foto'])

            # Input untuk pencarian dan filter
            search_query = st.text_input("Cari Nama atau Kelas:")
            min_date = df_presensi['tanggal'].min()
            max_date = df_presensi['tanggal'].max()
            selected_date = st.date_input("Pilih Tanggal", min_value=min_date, max_value=max_date, key="date_filter")

            # Filter DataFrame berdasarkan pencarian dan tanggal
            filtered_df = df_presensi

            if search_query:
                filtered_df = df_presensi[df_presensi.apply(lambda row: search_query.lower() in row['nama'].lower() or search_query.lower() in row['kelas'].lower(), axis=1)]

            if selected_date:
                filtered_df = filtered_df[filtered_df['tanggal'].dt.date == selected_date]

            # Jika tidak ada hasil setelah filter, tampilkan pesan informasi
            if filtered_df.empty:
                st.info("Tidak ada data yang sesuai dengan filter yang diterapkan.")
            else:
                # Buat HTML table dengan gambar dari DataFrame yang sudah difilter dan diurutkan
                table_html = "<table><tr><th>Nama</th><th>Kelas</th><th>Tanggal</th><th>Gambar</th></tr>"
                for index, data in filtered_df.iterrows():
                    nama = data.get('nama', '')
                    kelas = data.get('kelas', '')
                    tanggal = data.get('tanggal', '')
                    image_html = data.get('image', '')

                    # Tambahkan baris untuk setiap data
                    table_html += f"<tr><td>{nama}</td><td>{kelas}</td><td>{tanggal}</td><td>{image_html}</td></tr>"

                table_html += "</table>"

                # Tampilkan HTML table
                st.markdown(table_html, unsafe_allow_html=True)

        else:
            st.info("Belum ada data presensi.")
    else:
        st.error("Kode admin tidak valid.")

        
# Panggil fungsi admin jika berada dalam mode admin
admin_mode = st.experimental_get_query_params().get("admin", ["False"])[0]

if admin_mode == "True":
    admin()
else:
    main()
