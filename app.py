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

# Set your Supabase project URL and API key
supabase_url = "https://hmnsudaftcyngykefncr.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhtbnN1ZGFmdGN5bmd5a2VmbmNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDQ4ODA4NTcsImV4cCI6MjAyMDQ1Njg1N30.gfxRwUGG8Lb8G4YTsAfZCa0PLv2dc4SRsyD6RZhng1M"

# Connect to Supabase
client = Client(supabase_url, supabase_key)


def main():
    st.title("Form Presensi")

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
        stroke_color="white",
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


if __name__ == "__main__":
    main()
