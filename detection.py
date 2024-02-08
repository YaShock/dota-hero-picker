import cv2
import numpy as np
from mss import mss
from matplotlib import pyplot as plt


def get_hero_rois(img):
    """Get ROI polygons of hero portraits from an image during hero pick phase using contours.
    
    Args:
        img (array): An array representing the image (obtained through make_screenshot function)
    
    Returns:
        list[array(int)]: List of ROI polygons, which are arrays of 2D points
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 1, 15)

    # Close gaps
    kernel = np.ones((5, 5), np.uint8)
    img_closing = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    edges = img_closing

    # Find contours
    contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours
    rois = [] 
    for contour in contours:
        # Based on Y coodinates of contour
        if contour[0][0][1] > 80:
            continue
        cv2.drawContours(img, [contour], 0, (0, 255, 0), 1)

        # Approximate the contour to a polygon
        epsilon = 0.1 * cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, epsilon, True)
        
        # Check area
        cont_area = 8600
        cont_area_eps = 100

        area_correct = np.abs(cv2.contourArea(polygon) - cont_area) < 100

        # Check if the polygon has 4 sides and the aspect ratio is close to 1 
        aspect_correct = abs(1 - cv2.contourArea(polygon) / (cv2.boundingRect(polygon)[2] * cv2.boundingRect(polygon)[3])) < 0.2

        if len(polygon) == 4 and area_correct and aspect_correct:
            rois.append(polygon)

    return rois


def predefined_rois():
    """Get ROI polygons of hero portraits using predefined coordinates based on full HD resolution.
    This is a temporary working solution until contour based solution (or a new method) is fixed.
    
    Returns:
        list[array(int)]: List of ROI polygons, which are arrays of 2D points
    """
    rois = []
    roi_1 = np.array([[[1600,0],[1589,75],[1703,75],[1715,0]]])
    rois.append(roi_1)
    for i in range(4):
        roi = np.copy(roi_1)
        for p in range(4):
            roi[0][p][0] = roi_1[0][p][0] - 125 * (i + 1)
            roi[0][p][0] = roi_1[0][p][0] - 125 * (i + 1)
        rois.append(roi)

    roi_2 = np.array([[[702,0],[714,75],[828,75],[817,0]]])
    rois.append(roi_2)
    for i in range(4):
        roi = np.copy(roi_2)
        for p in range(4):
            roi[0][p][0] = roi_2[0][p][0] - 125 * (i + 1)
            roi[0][p][0] = roi_2[0][p][0] - 125 * (i + 1)
        rois.append(roi)

    return rois


def detect_heroes(heroes, img, rois, path_images):
    """Returns a list of heroes from an image given hero portrait positions. Each portrait is compared to the images of hero in the given folder.
    The image comparison is done using OpenCV's Brute-Force matcher of SIFT features.
    
    Args:
        heroes (json): JSON object containing constant data of each hero (obtained through queries.make_hero_info_query function)
        img (array): An array representing the image (obtained through make_screenshot function)
        rois (list[array(int)]): List of ROI polygons for coordinates of heroes' portraits
        path_images (str): Path to the folder containing images of heroes

    
    Returns:
        list[int]: List of detected heroes' IDs
    """
    hero_names = {}
    for hero in heroes['constants']['heroes']:
        hero_names[hero['id']] = hero['shortName']

    bf = cv2.BFMatcher()
    sift = cv2.SIFT_create()

    hero_des = {}

    for hero in heroes['constants']['heroes']:
        hero_name = hero['shortName']
        filename = path_images + '/' + hero_name + '.png'
        img_hero = cv2.imread(filename)
        kp, des = sift.detectAndCompute(img_hero, None)
        hero_des[hero['id']] = des

    matched_heroes = []

    # Compare each roi to loaded images based on SIFT
    for roi in rois:
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.fillPoly(mask, pts=[roi], color=(255, 255, 255))
        masked_img = cv2.bitwise_and(img,img,mask = mask)
        rect = cv2.boundingRect(roi)
        cropped = masked_img[rect[1]: rect[1] + rect[3], rect[0]: rect[0] + rect[2]]
        kp, des = sift.detectAndCompute(cropped, None)

        hero_matches = []

        for hero in heroes['constants']['heroes']:
            hero_id = hero['id']
            des_target = hero_des[hero_id]

            matches = bf.knnMatch(des, des_target, k=2)
            matches_count = 0
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    matches_count += 1
            hero_matches.append((hero_id, matches_count))
        hero_matches = sorted(hero_matches, key=lambda x: x[1], reverse=True)
        matched = hero_matches[0][0] if hero_matches[0][1] > 10 else None
        matched_display = hero_names[matched] if matched is not None else 'Not found'
        print(f'Best match: {matched_display} ({hero_matches[0][1]})')
        matched_heroes.append(matched)

    return matched_heroes


def make_screenshot(monitor_number, path):
    """Creates an image either from making a snapshot of the monitor or loading from file.
    
    Args:
        monitor_number (int): Number of the monitor to get screenshot of (only used when path is "live")
        path (str): Either "live" to capture the screen or a path to the image to load from file
    
    Returns:
        array: An array representing the image
    """
    if path != 'live':
        img = cv2.imread(path)
        return img

    with mss() as sct:
        mon = sct.monitors[monitor_number]
        img = np.array(sct.grab(mon))
        return img


def test_detection(monitor_number, screenshot_path, roi_method):
    """Creates an OpenCV window containing the image. Used for debugging.
    
    Args:
        monitor_number (int): Number of the monitor to get screenshot of (only used when screenshot_path is "live")
        screenshot_path (str): Either "live" to capture the screen or a path to the image to load from file
        roi_method (str): The method to detect ROIs, has to be either "predefined" or "contour"
    """
    # Get screenshot
    img = make_screenshot(monitor_number, screenshot_path)
    rois = predefined_rois() if roi_method == 'predefined' else get_hero_rois(img)

    img_rois = img.copy()
     
    # Draw ROIs
    for roi in rois:
        cv2.drawContours(img_rois, [roi], 0, (255, 0, 0), 2)
    
    # Show the result
    cv2.imshow('OpenCV/Numpy normal', img_rois)

    while True:
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break
