import tensorflow as tf
import os
import numpy as np
import cv2
import xml.etree.ElementTree as et
import random


class DataGenerator(tf.keras.utils.Sequence):

    def __init__(self, images_dir, labels_dir, batch_size, image_width, image_height):
        self.class_labels = ['person', 'aeroplane', 'bicycle', 'boat', 'bus', 'car', 'motorbike', 'train', 'bird',
                             'cat', 'cow', 'dog', 'horse', 'sheep', 'bottle', 'chair', 'diningtable', 'pottedplant',
                             'sofa', 'tvmonitor', 'none']
        self.batch_size = batch_size
        self.labels_dir = labels_dir
        labels = []
        for file_name in os.listdir(labels_dir):
            img_file = file_name.split(".")[0] + ".jpg"
            if os.path.isfile(os.path.join(images_dir, img_file)):
                image = cv2.imread(os.path.join(images_dir, img_file))
                if image is not None:
                    labels.append(file_name.split(".")[0])
        self.labels = labels
        self.images_dir = images_dir
        self.image_width = image_width
        self.image_height = image_height
        self.channels = 1
        self.indexes = np.arange(len(self.labels))
        self.label_dim = 2
        self.on_epoch_end()

    def __getitem__(self, index):
        indexes = self.indexes[index * self.batch_size: (index + 1) * self.batch_size]
        labels_temp = [self.labels[k] for k in indexes]
        x, y = self.__data_generation(labels_temp)
        return x, y

    def __len__(self):
        return int(np.floor(len(self.labels) / self.batch_size))

    def on_epoch_end(self):
        self.indexes = np.arange(len(self.labels))
        np.random.shuffle(self.labels)

    def __data_generation(self, labels_temp):
        x = np.empty((self.batch_size, self.image_height, self.image_width, self.channels))
        y = np.empty((self.batch_size, self.label_dim))
        for i, f in enumerate(labels_temp):
            image = cv2.imread(os.path.join(self.images_dir, f + ".jpg"))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            orig_width = int(image.shape[1])
            orig_height = int(image.shape[0])

            # Read ground truth
            bboxes = []
            tree = et.parse(os.path.join(self.labels_dir, f + ".xml"))
            root = tree.getroot()
            for obj in root.findall("./object"):
                label_name = obj.find('name').text
                label = self.class_labels.index(label_name)
                bndbox = obj.find('bndbox')
                xmin = int(bndbox.find('xmin').text)
                ymin = int(bndbox.find('ymin').text)
                xmax = int(bndbox.find('xmax').text)
                ymax = int(bndbox.find('ymax').text)
                bboxes.append((xmin, ymin, xmax, ymax, label))

            # Create object class window
            # Select random target object
            target_box = random.choice(bboxes)
            bboxes.remove(target_box)

            # Find image region with object (bbox + margin)
            if target_box[2] - target_box[0] > target_box[3] - target_box[1]:
                margin = int(float(target_box[2] - target_box[0]) * 0.2)
                window_xmin = max(target_box[0] - margin, 0)
                window_xmax = min(target_box[2] + margin, orig_width)
                window_ymin = max(target_box[1] - margin, 0)
                window_ymax = min(target_box[3] + margin, orig_height)
                cutout = image[window_ymin:window_ymax, window_xmin:window_xmax]
            else:
                margin = int(float(target_box[3] - target_box[1]) * 0.2)
                window_ymin = max(target_box[1] - margin, 0)
                window_ymax = min(target_box[3] + margin, orig_height)
                window_xmin = max(target_box[0] - margin, 0)
                window_xmax = min(target_box[2] + margin, orig_width)
                cutout = image[window_ymin:window_ymax, window_xmin:window_xmax]

            local_xmin = target_box[0] - window_xmin
            local_ymin = target_box[1] - window_ymin
            local_xmax = target_box[2] - window_xmax
            local_ymax = target_box[3] - window_ymax

            # Place image region centred on square black background
            if cutout.shape[1] > cutout.shape[0]:
                window = np.zeros((cutout.shape[1], cutout.shape[1]))
                margin = int((window.shape[0] - cutout.shape[0]) / 2)
                window[margin:(margin + cutout.shape[0]), :] = cutout
            else:
                window = np.zeros((cutout.shape[0], cutout.shape[0]))
                margin = int((window.shape[1] - cutout.shape[1]) / 2)
                window[:, margin:(margin + cutout.shape[1])] = cutout

            window_x_center = float(window.shape[1]) / 2.0
            window_y_center = float(window.shape[0]) / 2.0
            obj_x_center = (float(local_xmax - local_xmin) / 2.0) + float(local_xmin)
            obj_y_center = (float(local_ymax - local_ymin) / 2.0) + float(local_ymin)
            obj_x_offset = (window_x_center - obj_x_center) / float(window.shape[1])
            obj_y_offset = (window_y_center - obj_y_center) / float(window.shape[0])

            window = cv2.resize(window, (self.image_width, self.image_height))
            window = np.array(window, dtype=np.float)
            window /= 255.0
            window = np.reshape(window, (window.shape[0], window.shape[1], 1))

            x[i] = window
            y[i] = (obj_x_offset, obj_y_offset)

        return x, y