from services.ollama_ocr_service import OllamaOCRService

ocr = OllamaOCRService(
    ollama_endpoint="http://127.0.0.1:11434",
    model_name="glm-ocr:latest",
    timeout=180
)

result = ocr.process_image(r"C:\Users\KIIT0001\Desktop\minor\backend\samples\sampleocr.jpeg")
print(result)