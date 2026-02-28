import requests

url = "http://localhost:5000/api/ocr/image"

files = {
    "file": open("samples/french.png", "rb")
}

response = requests.post(url, files=files)

print("Status Code:", response.status_code)
print("Response JSON:")
print(response.json())