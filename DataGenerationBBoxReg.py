import tensorflow as tf
import os
import numpy as np
import cv2
import xml.etree.ElementTree as et
import random


class DataGenerator(tf.keras.utils.Sequence):

    def __init__(self, edge_images_dir, labels_dir, batch_size, image_width, image_height):
        self.batch_size = batch_size
        self.labels_dir = labels_dir
        labels = []
        for file_name in os.listdir(labels_dir):
            img_file = file_name.split(".")[0] + ".jpg"
            if os.path.isfile(os.path.join(edge_images_dir, img_file)):
                image = cv2.imread(os.path.join(edge_images_dir, img_file))
                if image is not None:
                    labels.append(file_name.split(".")[0])
        self.labels = labels
        self.edge_images_dir = edge_images_dir
        self.image_width = image_width
        self.image_height = image_height
        self.channels = 1
        self.indexes = np.arange(len(self.labels))
        self.label_dim = 4
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
            image = cv2.imread(os.path.join(self.edge_images_dir, f + ".jpg"))
            orig_width = int(image.shape[1])
            orig_height = int(image.shape[0])
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            bboxes = []
            tree = et.parse(os.path.join(self.labels_dir, f + ".xml"))
            root = tree.getroot()
            for bndbox in root.findall("./object/bndbox"):
                xmin = int(bndbox.find('xmin').text)
                ymin = int(bndbox.find('ymin').text)
                xmax = int(bndbox.find('xmax').text)
                ymax = int(bndbox.find('ymax').text)
                bboxes.append((xmin, ymin, xmax, ymax))
            target_box = random.choice(bboxes)
            window_xmin = np.random.randint(max(target_box[0] - 100, 0), target_box[0] + 1)
            window_ymin = np.random.randint(max(target_box[1] - 100, 0), target_box[1] + 1)
            window_xmax = np.random.randint(target_box[2], min(target_box[2] + 100, orig_width) + 1)
            window_ymax = np.random.randint(target_box[3], min(target_box[3] + 100, orig_height) + 1)

            window = image[window_ymin:window_ymax, window_xmin:window_xmax]
            window = cv2.resize(window, (self.image_width, self.image_height))
            window = np.array(window, dtype=np.float)
            window /= 255.0
            window = np.reshape(window, (window.shape[0], window.shape[1], 1))
            x[i] = window

            xmin = (float(target_box[0] - window_xmin) / float(window_xmax - window_xmin))
            ymin = (float(target_box[1] - window_ymin) / float(window_ymax - window_ymin))
            xmax = (float(target_box[2] - window_xmin) / float(window_xmax - window_xmin))
            ymax = (float(target_box[3] - window_ymin) / float(window_ymax - window_ymin))

            y[i] = (xmin, ymin, xmax, ymax)

        return x, y