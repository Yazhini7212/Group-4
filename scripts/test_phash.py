import cv2
from pathlib import Path

# Import the functions from the phash module
from chest_overlap.matching.phash import phash, hamming_distance
project_root = Path(__file__).resolve().parents[1]
image_dir = project_root / "data" / "test_images"

original = cv2.imread(
    str(image_dir / "xray_A.jpg"),
    cv2.IMREAD_GRAYSCALE
)

different_B = cv2.imread(
    str(image_dir / "xray_B.jpg"),
    cv2.IMREAD_GRAYSCALE
)

different_C = cv2.imread(
    str(image_dir / "xray_C.jpg"),
    cv2.IMREAD_GRAYSCALE
)

if any(img is None for img in [original, different_B, different_C]):
    raise FileNotFoundError("Check image paths and filenames.")



# 1. Generate transformed versions of image A
resized = cv2.resize(original, (256, 256))

compressed = cv2.imdecode(
    cv2.imencode(
        ".jpg", original,
        [cv2.IMWRITE_JPEG_QUALITY, 25]
    )[1],
    cv2.IMREAD_GRAYSCALE
)

h, w = original.shape
cropped = original[
    int(0.1 * h):int(0.9 * h),
    int(0.1 * w):int(0.9 * w)
]

# 2. Compute the hash of the original image
hash_A = phash(original)

# 3. Compare images and print results
print("A vs A:",
      hamming_distance(hash_A, phash(original)))

print("A vs Resized:",
      hamming_distance(hash_A, phash(resized)))

print("A vs Compressed:",
      hamming_distance(hash_A, phash(compressed)))

print("A vs Cropped:",
      hamming_distance(hash_A, phash(cropped)))

print("A vs B:",
      hamming_distance(hash_A, phash(different_B)))

print("A vs C:",
      hamming_distance(hash_A, phash(different_C)))



print("\nCropping experiment:")

h, w = original.shape

for ratio in [0, 0.05, 0.10, 0.15, 0.20, 0.25]:
    dh = int(h * ratio)
    dw = int(w * ratio)

    cropped = original[
        dh:h-dh,
        dw:w-dw
    ]

    distance = hamming_distance(
        hash_A, phash(cropped)
    )

    print(f"Crop {ratio*100:.0f}% per side: {distance}")
