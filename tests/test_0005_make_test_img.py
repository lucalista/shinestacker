from PIL import Image
import os


os.makedirs('output/img-jpg-wrong-size', exist_ok=True)
os.makedirs('output/img-tif-wrong-size', exist_ok=True)
os.makedirs('output/img-tif-wrong-type', exist_ok=True)
img1 = Image.new('RGB', (400, 600), color='black')
img2 = Image.new('RGB', (600, 400), color='black')
img1.save('output/img-jpg-wrong-size/image1.jpg', 'JPEG', quality=100)
img2.save('output/img-jpg-wrong-size/image2.jpg', 'JPEG', quality=100)
img1_16bit = img1.convert('I;16')
img2_16bit = img2.convert('I;16')
img1_16bit.save('output/img-tif-wrong-size/image1.tif', 'TIFF')
img2_16bit.save('output/img-tif-wrong-size/image2.tif', 'TIFF')
img1.save('output/img-tif-wrong-type/image_8bit.tif', 'TIFF')
img1_16bit.save('output/img-tif-wrong-type/image_16bit.tif', 'TIFF')
print("Test images successfully created")
