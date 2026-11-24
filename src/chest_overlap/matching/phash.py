import cv2  #pyhton Opencv library
import numpy as np #Nump = library fot numerical operations

def phash(image):
    # Resize the image to 32x32
    small = cv2.resize(image,(32, 32))
    
    # calculate the DCT (Discrete Cosine Transform) of the image
    # DCT = gray value to spatial frequency domain
    # Astype = change the data type
    dct = cv2.dct(small.astype(np.float32))

    # Choosing low frequency coefficients/slicing
    low_freq = dct[:8, :8]

    # Calculate the median of the low frequency coefficients
    median = np.median(low_freq.flatten()[1:])

    #Generate image fingerprint
    return low_freq > median

def hamming_distance(hash1, hash2):
    return int(np.count_nonzero(hash1 != hash2))


def compare(image1, image2):

    hash1 = phash(image1)
    hash2 = phash(image2)

    return hamming_distance(hash1, hash2)